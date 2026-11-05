import asyncio
import time
import bleach
import logging
from typing import Dict, Any, Optional, List
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select, update, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal, get_db
from app.models import (
    Trip, TripMember, ItineraryItem, ChatMessage, EventLog, User, VenueMetadata
)
from app.realtime.manager import manager
from app.realtime.board import Board, BoardItem
from app.budget.split import calculate_running_totals
from app.concierge.conflicts import detect_conflicts
from app.concierge.voting import VoteSession

from contextlib import asynccontextmanager

logger = logging.getLogger("warroom.handlers")


@asynccontextmanager
async def get_current_session():
    # In test context with dependency overrides, use the test session factory
    override = None
    try:
        from app.main import app
        override = app.dependency_overrides.get(get_db)
    except Exception:
        pass

    if override:
        gen = override()
        session = await gen.__anext__()
        try:
            yield session
        finally:
            try:
                await gen.__anext__()
            except StopAsyncIteration:
                pass
    else:
        async with SessionLocal() as session:
            yield session


def sanitize_text(text: str, max_length: int = 1000) -> str:
    cleaned = bleach.clean(text, tags=[], strip=True)
    return cleaned[:max_length].strip()


async def log_event(trip_id: int, user_id: Optional[int], event_type: str, payload: dict):
    """Appends an event to the append-only event log table."""
    try:
        async with get_current_session() as db:
            event_row = EventLog(
                trip_id=trip_id,
                user_id=user_id,
                type=event_type,
                payload=payload,
            )
            db.add(event_row)
            await db.commit()
    except Exception as e:
        logger.error(f"Failed to log event {event_type} for trip {trip_id}: {e}")


async def build_room_snapshot(trip_id: int) -> dict:
    board = manager.get_or_create_board(trip_id)
    items_snapshot = await board.get_snapshot()

    # Query recent chat messages (last 50) and participants from DB
    async with get_current_session() as db:
        trip = await db.get(Trip, trip_id)

        chat_stmt = (
            select(ChatMessage)
            .where(ChatMessage.trip_id == trip_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(50)
        )
        chat_res = await db.execute(chat_stmt)
        messages = [
            {
                "id": m.id,
                "userId": m.user_id,
                "userName": m.user_name,
                "messageType": m.message_type,
                "content": m.content,
                "createdAt": m.created_at.isoformat()
            }
            for m in reversed(chat_res.scalars().all())
        ]

        members_stmt = (
            select(TripMember, User)
            .join(User, TripMember.user_id == User.id)
            .where(TripMember.trip_id == trip_id)
        )
        members_res = await db.execute(members_stmt)
        members = [
            {
                "userId": u.id,
                "displayName": u.display_name,
                "role": tm.role,
                "budgetCeiling": u.budget_ceiling
            }
            for tm, u in members_res.all()
        ]

    # Calculate integer cents budget running totals
    member_ids = [m["userId"] for m in members]
    ceilings = {m["userId"]: m["budgetCeiling"] * 100 for m in members}
    items_with_cost = [
        {
            "id": it["id"],
            "cost_cents": int(it["pricePerPerson"] * 100 * max(1, len(member_ids))),
            "attendees": member_ids,
            "dayIndex": it["dayIndex"],
            "startMin": it["startMin"],
            "endMin": it["endMin"]
        }
        for it in items_snapshot
    ]
    running_totals = calculate_running_totals(items_with_cost, member_ids)

    # Detect active conflicts
    conflicts = detect_conflicts(items_snapshot, running_totals, ceilings)

    active_vote = manager.active_votes.get(trip_id)

    return {
        "tripId": trip_id,
        "title": trip.title if trip else "Trip",
        "destination": trip.destination if trip else "Lisbon",
        "country": trip.country if trip else "Portugal",
        "currency": trip.currency if trip else "EUR",
        "currencySymbol": trip.currency_symbol if trip else "€",
        "items": items_snapshot,
        "messages": messages,
        "members": members,
        "activeParticipants": list(manager.rooms.get(trip_id, {}).keys()),
        "budgetTotals": running_totals,
        "conflicts": conflicts,
        "activeVote": active_vote.to_dict() if active_vote else None,
        "frozen": manager.frozen_rooms.get(trip_id, False),
    }


async def dispatch_event(
    event_type: str,
    payload: dict,
    user: User,
    trip_id: int,
    user_role: str
):
    board = manager.get_or_create_board(trip_id)

    # 1. PING / PONG (Latency measurement)
    if event_type == "trip.sync.ping":
        server_now = int(time.time() * 1000)
        await manager.send_to_user(
            trip_id=trip_id,
            user_id=user.id,
            event="trip.sync.pong",
            payload={
                "clientSentAt": payload.get("clientSentAt"),
                "serverReceivedAt": server_now
            }
        )
        return

    # Check frozen state (Leader disconnect rule blocks structural changes)
    if manager.frozen_rooms.get(trip_id, False):
        if event_type in ("trip.board.lock", "trip.board.unlock", "trip.vote.open", "trip.vote.cast"):
            await manager.send_to_user(
                trip_id=trip_id,
                user_id=user.id,
                event="trip.action.rejected",
                payload={"reason": "Room actions are frozen while trip leader is disconnected."}
            )
            return

    # 2. BOARD PIN
    if event_type == "trip.board.pin":
        venue_id = payload.get("venueId")
        day_index = int(payload.get("dayIndex", 1))
        start_time = payload.get("startTime", "12:00")
        end_time = payload.get("endTime", "13:30")

        # Query venue details from DB to construct item
        async with get_current_session() as db:
            venue = await db.get(VenueMetadata, venue_id)
            if not venue:
                return

            db_item = ItineraryItem(
                trip_id=trip_id,
                venue_id=venue.id,
                day_index=day_index,
                start_time=start_time,
                end_time=end_time,
                start_min=int(start_time.split(":")[0]) * 60 + int(start_time.split(":")[1]),
                end_min=int(end_time.split(":")[0]) * 60 + int(end_time.split(":")[1]),
                lifecycle_stage="drafting",
                pinned_by_user_id=user.id,
                position_version=1
            )
            db.add(db_item)
            await db.commit()
            await db.refresh(db_item)

            board_item = BoardItem(
                id=db_item.id,
                trip_id=trip_id,
                venue_id=venue.id,
                venue_name=venue.name,
                category=venue.category,
                day_index=day_index,
                start_time=start_time,
                end_time=end_time,
                lifecycle_stage="drafting",
                pinned_by_user_id=user.id,
                position_version=1,
                price_per_person=venue.price_per_person,
                lat=venue.lat,
                lng=venue.lng
            )

        status, reason, item = await board.pin(board_item, user_role)
        if status == "ok":
            await log_event(trip_id, user.id, "board.item.pinned", item.to_dict())
            # Broadcast update and recalculate running totals & conflicts
            snapshot = await build_room_snapshot(trip_id)
            await manager.broadcast(trip_id, "trip.board.update", {
                "action": "pinned",
                "item": item.to_dict(),
                "budgetTotals": snapshot["budgetTotals"],
                "conflicts": snapshot["conflicts"]
            })

    # 3. BOARD MOVE (Optimistic concurrency with position_version)
    elif event_type == "trip.board.move":
        item_id = int(payload.get("itemId"))
        seen_version = int(payload.get("seenVersion", 1))
        day = int(payload.get("dayIndex", 1))
        start_time = payload.get("startTime", "12:00")
        end_time = payload.get("endTime", "13:30")

        status, reason, item = await board.move(
            item_id=item_id,
            seen_version=seen_version,
            day=day,
            start_time=start_time,
            end_time=end_time,
            actor_role=user_role
        )

        if status == "conflict":
            # Concurrency conflict! Send conflict event ONLY to the loser with current server state
            await manager.send_to_user(
                trip_id=trip_id,
                user_id=user.id,
                event="trip.board.conflict",
                payload={
                    "itemId": item_id,
                    "currentState": item.to_dict(),
                    "yourVersion": seen_version,
                    "message": "Another planner moved this item first. Updated to latest version."
                }
            )
        elif status == "rejected":
            await manager.send_to_user(
                trip_id=trip_id,
                user_id=user.id,
                event="trip.action.rejected",
                payload={"itemId": item_id, "reason": reason}
            )
        elif status == "ok":
            await log_event(trip_id, user.id, "board.item.moved", item.to_dict())
            snapshot = await build_room_snapshot(trip_id)
            await manager.broadcast(trip_id, "trip.board.update", {
                "action": "moved",
                "item": item.to_dict(),
                "budgetTotals": snapshot["budgetTotals"],
                "conflicts": snapshot["conflicts"]
            })

    # 4. BOARD LOCK / UNLOCK
    elif event_type in ("trip.board.lock", "trip.board.unlock"):
        item_id = int(payload.get("itemId"))
        target_stage = "locked" if event_type == "trip.board.lock" else "drafting"
        status, reason, item = await board.transition(item_id, target_stage, user_role)
        if status == "ok":
            await log_event(trip_id, user.id, f"board.item.{target_stage}", item.to_dict())
            # Immediately persist on lock
            async with get_current_session() as db:
                await db.execute(
                    update(ItineraryItem)
                    .where(ItineraryItem.id == item_id)
                    .values(lifecycle_stage=target_stage, position_version=item.position_version)
                )
                await db.commit()
            snapshot = await build_room_snapshot(trip_id)
            await manager.broadcast(trip_id, "trip.board.update", {
                "action": target_stage,
                "item": item.to_dict(),
                "budgetTotals": snapshot["budgetTotals"],
                "conflicts": snapshot["conflicts"]
            })
        else:
            await manager.send_to_user(
                trip_id=trip_id,
                user_id=user.id,
                event="trip.action.rejected",
                payload={"itemId": item_id, "reason": reason}
            )

    # 5. BOARD REMOVE
    elif event_type == "trip.board.remove":
        item_id = int(payload.get("itemId"))
        status, reason, item = await board.remove(item_id, user_role)
        if status == "ok":
            async with get_current_session() as db:
                it = await db.get(ItineraryItem, item_id)
                if it:
                    await db.delete(it)
                    await db.commit()
            await log_event(trip_id, user.id, "board.item.removed", {"itemId": item_id})
            snapshot = await build_room_snapshot(trip_id)
            await manager.broadcast(trip_id, "trip.board.update", {
                "action": "removed",
                "itemId": item_id,
                "budgetTotals": snapshot["budgetTotals"],
                "conflicts": snapshot["conflicts"]
            })

    # 6. CHAT MESSAGE
    elif event_type == "trip.chat.message":
        raw_content = payload.get("content", "")
        clean_content = sanitize_text(raw_content)
        if not clean_content:
            return

        async with get_current_session() as db:
            msg = ChatMessage(
                trip_id=trip_id,
                user_id=user.id,
                user_name=user.display_name,
                message_type="chat",
                content=clean_content
            )
            db.add(msg)
            await db.commit()
            await db.refresh(msg)

            msg_payload = {
                "id": msg.id,
                "userId": user.id,
                "userName": user.display_name,
                "messageType": "chat",
                "content": clean_content,
                "createdAt": msg.created_at.isoformat()
            }

        await log_event(trip_id, user.id, "chat.message", msg_payload)
        await manager.broadcast(trip_id, "trip.chat.message", msg_payload)

    # 7. CHAT TYPING (Broadcast only, not persisted)
    elif event_type == "trip.chat.typing":
        await manager.broadcast(
            trip_id=trip_id,
            event="trip.chat.typing",
            payload={"userId": user.id, "userName": user.display_name},
            exclude_user_id=user.id
        )

    # 8. CHAT REACTION (Broadcast only, not persisted)
    elif event_type == "trip.chat.reaction":
        message_id = payload.get("messageId")
        emoji = sanitize_text(payload.get("emoji", "👍"), max_length=10)
        await manager.broadcast(
            trip_id=trip_id,
            event="trip.chat.reaction",
            payload={"messageId": message_id, "emoji": emoji, "userId": user.id, "userName": user.display_name}
        )

    # 9. VOTING: OPEN
    elif event_type == "trip.vote.open":
        if user_role not in ("planner", "leader", "admin"):
            return
        item_ids = [int(x) for x in payload.get("itemIds", [])]
        if len(item_ids) < 2:
            return

        # Freeze candidates: transition all items to 'voting' stage
        for iid in item_ids:
            await board.transition(iid, "voting", user_role)

        vote_id = f"vote_{trip_id}_{int(time.time())}"
        duration = int(payload.get("durationSeconds", 30))

        async def resolve_callback(sess: VoteSession):
            await resolve_vote(trip_id, sess)

        vote_session = VoteSession(
            vote_id=vote_id,
            trip_id=trip_id,
            item_ids=item_ids,
            duration_seconds=duration,
            opened_by_user_id=user.id,
            on_resolve=resolve_callback
        )
        manager.active_votes[trip_id] = vote_session
        vote_session.start_timer()

        await log_event(trip_id, user.id, "vote.opened", vote_session.to_dict())
        snapshot = await build_room_snapshot(trip_id)
        await manager.broadcast(trip_id, "trip.vote.opened", {
            "vote": vote_session.to_dict(),
            "items": snapshot["items"]
        })

    # 10. VOTING: CAST
    elif event_type == "trip.vote.cast":
        vote_session = manager.active_votes.get(trip_id)
        if not vote_session or vote_session.resolved:
            return
        item_id = int(payload.get("itemId"))
        total_voters = len(manager.rooms.get(trip_id, {}))
        should_early_close = vote_session.cast_vote(user.id, item_id, user_role, total_eligible_voters=total_voters)
        
        await log_event(trip_id, user.id, "vote.cast", {"voteId": vote_session.vote_id, "itemId": item_id})
        await manager.broadcast(trip_id, "trip.vote.cast", {
            "voteId": vote_session.vote_id,
            "userId": user.id,
            "votesCount": len(vote_session.votes)
        })

        if should_early_close:
            await resolve_vote(trip_id, vote_session)


async def resolve_vote(trip_id: int, vote_session: VoteSession):
    board = manager.get_or_create_board(trip_id)
    async with board.lock:
        if vote_session.resolved and vote_session.winner_item_id is not None:
            return

        # Fetch pinned timestamps from board items
        pinned_ts = {iid: getattr(it, "pinned_by_user_id", 0) for iid, it in board.items.items()}
        winner_id = vote_session.tally(pinned_ts)

        # Winner becomes locked; others in contested vote are removed
        for iid in vote_session.item_ids:
            if iid == winner_id:
                if iid in board.items:
                    board.items[iid].lifecycle_stage = "locked"
                    board.items[iid].position_version += 1
                    board.items[iid].dirty = True
            else:
                if iid in board.items:
                    del board.items[iid]

        # Sync to DB
        async with get_current_session() as db:
            for iid in vote_session.item_ids:
                if iid == winner_id:
                    await db.execute(
                        update(ItineraryItem)
                        .where(ItineraryItem.id == iid)
                        .values(lifecycle_stage="locked")
                    )
                else:
                    await db.execute(
                        update(ItineraryItem)
                        .where(ItineraryItem.id == iid)
                        .values(lifecycle_stage="removed")
                    )
            await db.commit()

        manager.active_votes.pop(trip_id, None)

        snapshot_items = [it.to_dict() for it in board.items.values()]

    await log_event(trip_id, None, "vote.resolved", vote_session.to_dict())
    snapshot = await build_room_snapshot(trip_id)

    # Fan-out trip.vote.resolved and updated board simultaneously
    await manager.broadcast(trip_id, "trip.vote.resolved", {
        "vote": vote_session.to_dict(),
        "winnerItemId": winner_id,
        "items": snapshot["items"],
        "budgetTotals": snapshot["budgetTotals"],
        "conflicts": snapshot["conflicts"]
    })


async def start_batched_persistence():
    """Background task flushing dirty items to DB every 2 seconds."""
    while True:
        try:
            await asyncio.sleep(2)
            for trip_id, board in list(manager.boards.items()):
                dirty_items = await board.get_dirty_items()
                if dirty_items:
                    async with SessionLocal() as db:
                        for it in dirty_items:
                            await db.execute(
                                update(ItineraryItem)
                                .where(ItineraryItem.id == it.id)
                                .values(
                                    day_index=it.day_index,
                                    start_time=it.start_time,
                                    end_time=it.end_time,
                                    start_min=it.start_min,
                                    end_min=it.end_min,
                                    lifecycle_stage=it.lifecycle_stage,
                                    position_version=it.position_version,
                                )
                            )
                        await db.commit()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in batched persistence: {e}")

import datetime
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db import get_db
from app.models import Trip, TripMember, User, EventLog, Interaction, VenueMetadata, ItineraryItem
from app.schemas import TripAnalytics
from app.security import current_user, get_room_role
from app.realtime.manager import manager

router = APIRouter(tags=["Dashboard & Analytics"])


@router.get("/api/v1/me/dashboard")
async def get_user_dashboard(
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Past trips
    trips_stmt = (
        select(Trip, TripMember.role)
        .join(TripMember, Trip.id == TripMember.trip_id)
        .where(TripMember.user_id == user.id)
        .order_by(Trip.created_at.desc())
    )
    trips_res = await db.execute(trips_stmt)
    user_trips = []
    active_rooms = []
    for trip, role in trips_res.all():
        is_active = trip.id in manager.rooms and len(manager.rooms[trip.id]) > 0
        trip_info = {
            "id": trip.id,
            "title": trip.title,
            "destination": trip.destination,
            "inviteCode": trip.invite_code,
            "role": role,
            "createdAt": trip.created_at.isoformat(),
            "isActive": is_active,
            "activeParticipants": manager.get_active_participant_count(trip.id)
        }
        user_trips.append(trip_info)
        if is_active:
            active_rooms.append(trip_info)

    # 2. Derived preferences from interactions and user profile
    inter_stmt = select(Interaction, VenueMetadata).join(
        VenueMetadata, Interaction.venue_id == VenueMetadata.id
    ).where(Interaction.user_id == user.id)
    inter_res = await db.execute(inter_stmt)
    interactions = inter_res.all()

    category_counts: Dict[str, int] = {}
    prices = [user.budget_ceiling]

    for inter, venue in interactions:
        cat = venue.category
        category_counts[cat] = category_counts.get(cat, 0) + 1
        prices.append(venue.price_per_person)

    top_categories = sorted(category_counts.keys(), key=lambda c: category_counts[c], reverse=True)[:3]
    min_budget = min(prices) if prices else 10.0
    max_budget = max(prices) if prices else float(user.budget_ceiling)

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "displayName": user.display_name,
            "role": user.role,
            "budgetCeiling": user.budget_ceiling,
            "dietaryTags": user.dietary_tags
        },
        "preferences": {
            "budgetRange": {"min": min_budget, "max": max_budget},
            "frequentDietaryTags": user.dietary_tags,
            "topCategories": top_categories or ["dinner", "activity", "lunch"]
        },
        "trips": user_trips,
        "activeRooms": active_rooms
    }


@router.get("/api/v1/trips/{trip_id}/analytics", response_model=TripAnalytics)
async def get_trip_analytics(
    trip_id: int,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db)
):
    await get_room_role(user, trip_id, db)

    # Strict reconciliation derived from append-only events table
    events_stmt = (
        select(EventLog)
        .where(EventLog.trip_id == trip_id)
        .order_by(EventLog.ts.asc())
    )
    res = await db.execute(events_stmt)
    events = res.scalars().all()

    if not events:
        return TripAnalytics(
            tripId=trip_id,
            planningDurationMinutes=0.0,
            peakConcurrentPlanners=1,
            aiQuestionsCount=0,
            conflictsFlagged=0,
            conflictsResolved=0,
            perPersonBreakdown={}
        )

    first_event_ts = events[0].ts
    last_event_ts = events[-1].ts
    duration_minutes = max(0.1, round((last_event_ts - first_event_ts).total_seconds() / 60.0, 2))

    peak_planners = 1
    ai_questions_count = 0
    conflicts_flagged = 0
    conflicts_resolved = 0

    for ev in events:
        if ev.type in ("trip.presence.update", "presence.update", "presence.join"):
            cnt = ev.payload.get("participantCount", 1)
            if cnt > peak_planners:
                peak_planners = cnt
        elif ev.type == "ai.asked":
            ai_questions_count += 1
        elif "conflict" in ev.type or ev.type == "conflict.flagged":
            conflicts_flagged += 1
        elif ev.type in ("conflict.resolved", "vote.resolved"):
            conflicts_resolved += 1

    # Per-person breakdown derived from trip itinerary items
    items_stmt = (
        select(ItineraryItem, VenueMetadata)
        .join(VenueMetadata, ItineraryItem.venue_id == VenueMetadata.id)
        .where(ItineraryItem.trip_id == trip_id)
    )
    items_res = await db.execute(items_stmt)
    items_data = items_res.all()

    # Members count
    members_count_stmt = select(func.count(TripMember.user_id)).where(TripMember.trip_id == trip_id)
    members_count = (await db.execute(members_count_stmt)).scalar() or 1

    total_cost = sum(v.price_per_person for _, v in items_data)
    per_person_share = round(total_cost / max(1, members_count), 2)

    # Member user ids
    mems_stmt = select(TripMember.user_id).where(TripMember.trip_id == trip_id)
    uids = (await db.execute(mems_stmt)).scalars().all()
    per_person_breakdown = {uid: per_person_share for uid in uids}

    return TripAnalytics(
        tripId=trip_id,
        planningDurationMinutes=duration_minutes,
        peakConcurrentPlanners=peak_planners,
        aiQuestionsCount=ai_questions_count,
        conflictsFlagged=conflicts_flagged,
        conflictsResolved=conflicts_resolved,
        perPersonBreakdown=per_person_breakdown
    )

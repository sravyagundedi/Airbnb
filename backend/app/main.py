import asyncio
import os
import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func

from app.config import settings
from app.logging_conf import configure_logging
from app.db import init_db, SessionLocal, get_db
from app.models import VenueMetadata, Trip, TripMember, ItineraryItem, User
from app.security import auth_from_token, get_room_role
from app.realtime.manager import manager
from app.realtime.board import BoardItem
from app.realtime.handlers import (
    dispatch_event, build_room_snapshot, log_event, start_batched_persistence
)
from app.reco.train import train_and_evaluate
from app.reco.serve import recommender_service
from scripts.gen_interactions import generate_synthetic_data

# Import REST routers
from app.routers import auth, trips, venues, ai, dashboard, admin, health, expenses


configure_logging(settings.LOG_LEVEL)
logger = logging.getLogger("warroom.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database schema...")
    await init_db()

    # Seed venues if empty
    async with SessionLocal() as db:
        cnt_stmt = select(func.count(VenueMetadata.id))
        venue_count = (await db.execute(cnt_stmt)).scalar() or 0
        if venue_count == 0:
            logger.info("Venue catalog empty. Auto-seeding Lisbon venues...")
            from scripts.seed_venues import seed_venues
            await seed_venues()

    # Seed default demo accounts if they don't exist
    async with SessionLocal() as db:
        demo_accounts = [
            ("leader@warroom.local", "Password123!", "Trip Leader", "leader", 200, ["vegetarian"]),
            ("planner@warroom.local", "Password123!", "Trip Planner", "planner", 150, ["vegetarian", "gluten-free"]),
            ("viewer@warroom.local", "Password123!", "Trip Viewer", "viewer", 100, []),
            ("admin@warroom.local", "Password123!", "System Admin", "admin", 300, []),
        ]
        from app.security import hash_password
        for d_email, d_pwd, d_name, d_role, d_ceiling, d_tags in demo_accounts:
            stmt = select(User).where(func.lower(User.email) == d_email.lower())
            exists = (await db.execute(stmt)).scalar_one_or_none()
            if not exists:
                u = User(
                    email=d_email,
                    password_hash=hash_password(d_pwd),
                    display_name=d_name,
                    role=d_role,
                    budget_ceiling=d_ceiling,
                    dietary_tags=d_tags
                )
                db.add(u)
        await db.commit()

    # Initialize Recommender system
    venues_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "lisbon_venues.json")
    inter_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "synthetic_interactions.json")
    if not os.path.exists(inter_path):
        generate_synthetic_data()

    if os.path.exists(venues_path) and os.path.exists(inter_path):
        with open(venues_path, "r", encoding="utf-8") as f:
            v_data = json.load(f)
        with open(inter_path, "r", encoding="utf-8") as f:
            i_data = json.load(f)
        train_and_evaluate(i_data, v_data)
        recommender_service.load_artifacts()

    # Start background batched persistence task (every 2s)
    manager.persistence_task = asyncio.create_task(start_batched_persistence())
    logger.info("WarRoom logistics engine and gateway initialized successfully.")

    yield

    # Teardown
    if manager.persistence_task:
        manager.persistence_task.cancel()
    logger.info("WarRoom shutdown complete.")


app = FastAPI(
    title="AI Trip War Room",
    description="Collaborative Group Itinerary Canvas & Real-Time Logistics Engine",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(auth.router)
app.include_router(trips.router)
app.include_router(venues.router)
app.include_router(expenses.router)
app.include_router(ai.router)
app.include_router(dashboard.router)
app.include_router(admin.router)
app.include_router(health.router)



@asynccontextmanager
async def get_ws_session():
    override = app.dependency_overrides.get(get_db)
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


@app.websocket("/ws/trips/{trip_id}")
async def trip_room_websocket(
    ws: WebSocket,
    trip_id: int,
    token: str = Query(...)
):
    # 1. Authenticate user from JWT token during handshake
    async with get_ws_session() as db:
        try:
            user = await auth_from_token(token, db)
        except Exception:
            await ws.close(code=4401, reason="Invalid authentication token")
            return

        # 2. Check room membership and determine room-level role
        try:
            user_role = await get_room_role(user, trip_id, db)
        except Exception:
            await ws.close(code=4403, reason="Forbidden: Not a member of this trip room")
            return

        # 3. Load trip items into memory board if not already active
        if trip_id not in manager.boards:
            items_stmt = (
                select(ItineraryItem, VenueMetadata)
                .join(VenueMetadata, ItineraryItem.venue_id == VenueMetadata.id)
                .where(ItineraryItem.trip_id == trip_id)
            )
            res = await db.execute(items_stmt)
            board_items = []
            for it, v in res.all():
                board_items.append(BoardItem(
                    id=it.id,
                    trip_id=trip_id,
                    venue_id=v.id,
                    venue_name=v.name,
                    category=v.category,
                    day_index=it.day_index,
                    start_time=it.start_time,
                    end_time=it.end_time,
                    lifecycle_stage=it.lifecycle_stage,
                    pinned_by_user_id=it.pinned_by_user_id,
                    position_version=it.position_version,
                    price_per_person=v.price_per_person,
                    lat=v.lat,
                    lng=v.lng
                ))
            manager.get_or_create_board(trip_id, board_items)

        # Record trip leader
        trip_obj = await db.get(Trip, trip_id)
        if trip_obj:
            manager.trip_leaders[trip_id] = trip_obj.creator_id

    # 4. Accept connection
    await ws.accept()

    # Reconnect handling: cancel pending leave timer if user reconnected within 10s
    was_pending = manager.cancel_pending_leave(trip_id, user.id)

    # Leader disconnect rule handling
    is_leader = (user_role == "leader" or manager.trip_leaders.get(trip_id) == user.id)
    if is_leader:
        manager.on_leader_reconnected(trip_id)

    manager.rooms.setdefault(trip_id, {})[user.id] = ws

    # Send full authoritative room snapshot immediately
    snapshot = await build_room_snapshot(trip_id)
    await ws.send_json({
        "event": "trip.room.snapshot",
        "tripId": trip_id,
        "payload": snapshot
    })

    # Broadcast presence update only if not an instant reconnect
    if not was_pending:
        await manager.broadcast(
            trip_id=trip_id,
            event="trip.presence.update",
            payload={
                "participantId": user.id,
                "displayName": user.display_name,
                "role": user_role,
                "action": "joined",
                "participantCount": len(manager.rooms[trip_id])
            }
        )
        await log_event(trip_id, user.id, "trip.presence.update", {
            "participantId": user.id, "action": "joined", "participantCount": len(manager.rooms[trip_id])
        })

    # Message reception loop
    try:
        while True:
            data = await ws.receive_json()
            event = data.get("event")
            payload = data.get("payload", {})
            if event:
                await dispatch_event(
                    event_type=event,
                    payload=payload,
                    user=user,
                    trip_id=trip_id,
                    user_role=user_role
                )
    except WebSocketDisconnect:
        # User disconnected
        manager.rooms.get(trip_id, {}).pop(user.id, None)
        if trip_id in manager.rooms and not manager.rooms[trip_id]:
            manager.rooms.pop(trip_id, None)

        active_count = len(manager.rooms.get(trip_id, {}))

        # Schedule pending leave with 10s grace
        async def delayed_leave_notification():
            try:
                await asyncio.sleep(10)
                await manager.broadcast(
                    trip_id=trip_id,
                    event="trip.presence.update",
                    payload={
                        "participantId": user.id,
                        "displayName": user.display_name,
                        "role": user_role,
                        "action": "left",
                        "participantCount": len(manager.rooms.get(trip_id, {}))
                    }
                )
                await log_event(trip_id, user.id, "trip.presence.update", {
                    "participantId": user.id, "action": "left", "participantCount": len(manager.rooms.get(trip_id, {}))
                })
            except asyncio.CancelledError:
                pass

        leave_task = asyncio.create_task(delayed_leave_notification())
        manager.pending_leaves[(trip_id, user.id)] = leave_task

        # If leader disconnected, schedule 15s grace rule
        if is_leader:
            manager.schedule_leader_disconnect_rule(trip_id)

import pytest
import os
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import User, Trip, TripMember, VenueMetadata, VenueDietaryTag
from app.security import hash_password, make_access_token

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
async def async_client():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def seed_users_and_trip():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as db:
        admin = User(
            id=1,
            email="admin@warroom.local",
            password_hash=hash_password("adminpass123"),
            display_name="Admin User",
            role="admin",
            budget_ceiling=300
        )
        leader = User(
            id=2,
            email="leader@warroom.local",
            password_hash=hash_password("leaderpass123"),
            display_name="Trip Leader",
            role="leader",
            budget_ceiling=150
        )
        planner = User(
            id=3,
            email="planner@warroom.local",
            password_hash=hash_password("plannerpass123"),
            display_name="Trip Planner",
            role="planner",
            budget_ceiling=100
        )
        viewer = User(
            id=4,
            email="viewer@warroom.local",
            password_hash=hash_password("viewerpass123"),
            display_name="Trip Viewer",
            role="viewer",
            budget_ceiling=80
        )
        db.add_all([admin, leader, planner, viewer])
        await db.commit()

        # Seed sample trip
        trip = Trip(
            id=1,
            title="Lisbon War Room",
            destination="Lisbon",
            invite_code="AB-TEST",
            max_participants=5,
            creator_id=2
        )
        db.add(trip)
        await db.flush()

        # Memberships
        db.add(TripMember(trip_id=1, user_id=2, role="leader"))
        db.add(TripMember(trip_id=1, user_id=3, role="planner"))
        db.add(TripMember(trip_id=1, user_id=4, role="viewer"))

        # Seed sample venue
        venue = VenueMetadata(
            id="v_3391",
            name="Taberna da Rua",
            category="dinner",
            price_per_person=22.0,
            destination="Lisbon",
            lat=38.7139,
            lng=-9.1394,
            rating=4.4,
            open_time="11:00",
            close_time="22:00",
            open_min=660,
            close_min=1320,
            description="Test Lisbon tavern."
        )
        db.add(venue)
        db.add(VenueDietaryTag(venue_id="v_3391", tag="vegetarian"))
        await db.commit()

    tokens = {
        "admin_token": make_access_token(1, "admin"),
        "leader_token": make_access_token(2, "leader"),
        "planner_token": make_access_token(3, "planner"),
        "viewer_token": make_access_token(4, "viewer"),
        "trip_id": 1,
        "venue_id": "v_3391"
    }

    yield tokens

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

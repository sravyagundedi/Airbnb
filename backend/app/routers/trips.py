import secrets
import string
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db import get_db
from app.models import Trip, TripMember, User
from app.schemas import TripCreateRequest, TripJoinRequest, TripResponse, TripMemberResponse
from app.security import current_user, require_role, get_room_role
from app.destinations import resolve_country_and_currency

router = APIRouter(prefix="/api/v1/trips", tags=["Trips"])


def generate_invite_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    suffix = "".join(secrets.choice(alphabet) for _ in range(4))
    return f"AB-{suffix}"


@router.post("", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
async def create_trip(
    req: TripCreateRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db)
):
    invite_code = generate_invite_code()

    # Resolve country, destination, currency, and symbol dynamically
    country, destination, currency, symbol, _, _ = resolve_country_and_currency(
        country=req.country,
        destination=req.destination
    )
    if req.currency:
        currency = req.currency

    trip = Trip(
        title=req.title,
        destination=destination,
        country=country,
        currency=currency,
        currency_symbol=symbol,
        invite_code=invite_code,
        max_participants=req.max_participants,
        creator_id=user.id
    )
    db.add(trip)
    await db.flush()

    # Creator is automatically assigned role 'leader' in trip_members
    membership = TripMember(
        trip_id=trip.id,
        user_id=user.id,
        role="leader"
    )
    db.add(membership)
    await db.commit()
    await db.refresh(trip)

    return TripResponse(
        id=trip.id,
        title=trip.title,
        destination=trip.destination,
        country=trip.country,
        currency=trip.currency,
        currency_symbol=trip.currency_symbol,
        invite_code=trip.invite_code,
        max_participants=trip.max_participants,
        creator_id=trip.creator_id,
        created_at=trip.created_at,
        members_count=1
    )


@router.post("/join", response_model=TripResponse)
async def join_trip(
    req: TripJoinRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Trip).where(Trip.invite_code == req.inviteCode)
    trip = (await db.execute(stmt)).scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip room not found for this invite code")

    # Check existing membership
    mem_stmt = select(TripMember).where(TripMember.trip_id == trip.id, TripMember.user_id == user.id)
    existing_member = (await db.execute(mem_stmt)).scalar_one_or_none()

    count_stmt = select(func.count(TripMember.user_id)).where(TripMember.trip_id == trip.id)
    current_count = (await db.execute(count_stmt)).scalar() or 0

    if existing_member:
        return TripResponse(
            id=trip.id,
            title=trip.title,
            destination=trip.destination,
            country=trip.country or "Portugal",
            currency=trip.currency or "EUR",
            currency_symbol=trip.currency_symbol or "€",
            invite_code=trip.invite_code,
            max_participants=trip.max_participants,
            creator_id=trip.creator_id,
            created_at=trip.created_at,
            members_count=current_count
        )

    # Check capacity limit
    if current_count >= trip.max_participants:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Trip room capacity reached ({trip.max_participants} max participants)"
        )

    # Join as planner (or viewer if user role is viewer)
    assigned_role = "viewer" if user.role == "viewer" else "planner"
    new_member = TripMember(
        trip_id=trip.id,
        user_id=user.id,
        role=assigned_role
    )
    db.add(new_member)
    await db.commit()

    return TripResponse(
        id=trip.id,
        title=trip.title,
        destination=trip.destination,
        country=trip.country or "Portugal",
        currency=trip.currency or "EUR",
        currency_symbol=trip.currency_symbol or "€",
        invite_code=trip.invite_code,
        max_participants=trip.max_participants,
        creator_id=trip.creator_id,
        created_at=trip.created_at,
        members_count=current_count + 1
    )


@router.get("", response_model=List[TripResponse])
async def list_my_trips(
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Trip, func.count(TripMember.user_id).label("members_count"))
        .join(TripMember, Trip.id == TripMember.trip_id)
        .where(TripMember.user_id == user.id)
        .group_by(Trip.id)
        .order_by(Trip.created_at.desc())
    )
    results = await db.execute(stmt)
    trips = []
    for trip, count in results.all():
        trips.append(TripResponse(
            id=trip.id,
            title=trip.title,
            destination=trip.destination,
            country=trip.country or "Portugal",
            currency=trip.currency or "EUR",
            currency_symbol=trip.currency_symbol or "€",
            invite_code=trip.invite_code,
            max_participants=trip.max_participants,
            creator_id=trip.creator_id,
            created_at=trip.created_at,
            members_count=count
        ))
    return trips


@router.get("/{trip_id}/members", response_model=List[TripMemberResponse])
async def get_trip_members(
    trip_id: int,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify membership
    await get_room_role(user, trip_id, db)

    stmt = (
        select(TripMember, User)
        .join(User, TripMember.user_id == User.id)
        .where(TripMember.trip_id == trip_id)
    )
    results = await db.execute(stmt)
    members = []
    for tm, u in results.all():
        members.append(TripMemberResponse(
            user_id=u.id,
            display_name=u.display_name,
            email=u.email,
            role=tm.role,
            joined_at=tm.joined_at
        ))
    return members

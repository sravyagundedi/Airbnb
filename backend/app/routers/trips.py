import secrets
import string
import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db import get_db
from app.models import Trip, TripMember, User, ItemComment, ItineraryItem, EventLog
from app.schemas import (
    TripCreateRequest, TripJoinRequest, TripResponse, TripMemberResponse,
    EstimateBudgetRequest, EstimateBudgetResponse, DailyCostBreakdown,
    ItemCommentCreateRequest, ItemCommentResponse
)
from app.security import current_user, require_role, get_room_role
from app.destinations import resolve_country_and_currency, COUNTRY_DIRECTORY

COUNTRY_COST_INDEX = {
    "Switzerland": 1.5,
    "United States": 1.25,
    "United Kingdom": 1.2,
    "Australia": 1.15,
    "France": 1.05,
    "Germany": 1.0,
    "Japan": 0.95,
    "Canada": 1.05,
    "Italy": 0.9,
    "Spain": 0.85,
    "Portugal": 0.8,
    "Greece": 0.75,
    "United Arab Emirates": 1.2,
    "Singapore": 1.25,
    "South Korea": 0.9,
    "Mexico": 0.55,
    "Brazil": 0.5,
    "Thailand": 0.45,
    "India": 0.35,
    "Vietnam": 0.35,
}

CURRENCY_CONVERSION = {
    "EUR": 1.0,
    "USD": 1.08,
    "GBP": 0.85,
    "JPY": 165.0,
    "INR": 90.0,
    "CAD": 1.48,
    "AUD": 1.65,
    "CHF": 0.95,
    "AED": 3.97,
    "SGD": 1.45,
    "KRW": 1450.0,
    "BRL": 5.5,
    "MXN": 18.5,
    "THB": 39.0,
    "VND": 27000.0,
}


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


@router.post("/estimate-budget", response_model=EstimateBudgetResponse)
async def estimate_budget(req: EstimateBudgetRequest):
    """
    Computes a realistic pre-trip budget forecast based on destination, duration,
    traveler count, travel style, and selected currency.
    """
    country, destination, currency, symbol, _, _ = resolve_country_and_currency(
        country=req.country,
        destination=req.destination
    )
    if req.currency:
        currency = req.currency
        # Find symbol if available
        for cdata in COUNTRY_DIRECTORY.values():
            if cdata.get("currency") == currency:
                symbol = cdata.get("symbol", symbol)
                break

    cost_idx = COUNTRY_COST_INDEX.get(country, 1.0)
    curr_rate = CURRENCY_CONVERSION.get(currency, 1.0)

    # Style multipliers
    style = req.travel_style.lower()
    if style == "budget":
        style_mult = 0.55
        lodging_base = 35.0
        food_base = 22.0
        act_base = 12.0
        transit_base = 6.0
    elif style == "luxury":
        style_mult = 2.6
        lodging_base = 220.0
        food_base = 110.0
        act_base = 70.0
        transit_base = 35.0
    else:  # balanced
        style = "balanced"
        style_mult = 1.0
        lodging_base = 75.0
        food_base = 45.0
        act_base = 25.0
        transit_base = 12.0

    factor = cost_idx * curr_rate
    lodging = round(lodging_base * factor, 2)
    food = round(food_base * factor, 2)
    activities = round(act_base * factor, 2)
    transit = round(transit_base * factor, 2)
    buffer = round((lodging + food + activities + transit) * 0.15, 2)

    daily_per_person = DailyCostBreakdown(
        lodging=lodging,
        food=food,
        activities=activities,
        transit=transit,
        buffer=buffer
    )

    daily_sum = lodging + food + activities + transit + buffer
    per_person_total = round(daily_sum * req.duration_days, 2)
    total_trip_cost = round(per_person_total * req.travelers_count, 2)

    category_totals = {
        "lodging": round(lodging * req.duration_days * req.travelers_count, 2),
        "food": round(food * req.duration_days * req.travelers_count, 2),
        "activities": round(activities * req.duration_days * req.travelers_count, 2),
        "transit": round(transit * req.duration_days * req.travelers_count, 2),
        "buffer": round(buffer * req.duration_days * req.travelers_count, 2),
    }

    tips = [
        f"In {destination} ({country}), booking accommodations 4-6 weeks ahead saves ~18%.",
        f"Daily food estimate of {symbol}{food:.0f}/person covers authentic local dining and cafes.",
        f"Emergency buffer of 15% ({symbol}{buffer:.0f}/day) protects against unexpected logistics fees.",
        f"Group of {req.travelers_count} can split shared transit and apartment rentals for extra savings."
    ]

    return EstimateBudgetResponse(
        destination=destination,
        country=country,
        currency=currency,
        currency_symbol=symbol,
        duration_days=req.duration_days,
        travelers_count=req.travelers_count,
        travel_style=style,
        daily_per_person=daily_per_person,
        total_trip_cost=total_trip_cost,
        per_person_total=per_person_total,
        category_totals=category_totals,
        recommendations=tips
    )


@router.get("/{trip_id}/items/{item_id}/comments", response_model=List[ItemCommentResponse])
async def get_item_comments(
    trip_id: int,
    item_id: int,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db)
):
    role = await get_room_role(user, trip_id, db)
    if not role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Must be a member of the trip room")

    stmt = (
        select(ItemComment)
        .where(ItemComment.trip_id == trip_id, ItemComment.item_id == item_id)
        .order_by(ItemComment.created_at.asc())
    )
    comments = (await db.execute(stmt)).scalars().all()
    return comments


@router.post("/{trip_id}/items/{item_id}/comments", response_model=ItemCommentResponse, status_code=status.HTTP_201_CREATED)
async def create_item_comment(
    trip_id: int,
    item_id: int,
    req: ItemCommentCreateRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db)
):
    role = await get_room_role(user, trip_id, db)

    if not role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Must be a member of the trip room")

    item = await db.get(ItineraryItem, item_id)
    if not item or item.trip_id != trip_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary item not found in this trip")

    comment = ItemComment(
        item_id=item_id,
        trip_id=trip_id,
        user_id=user.id,
        user_name=user.display_name,
        content=req.content.strip(),
        created_at=datetime.datetime.utcnow()
    )
    db.add(comment)

    log = EventLog(
        trip_id=trip_id,
        user_id=user.id,
        type="item_comment_added",
        payload={"item_id": item_id, "author": user.display_name, "content": comment.content[:50]}
    )
    db.add(log)
    await db.commit()
    await db.refresh(comment)

    return comment


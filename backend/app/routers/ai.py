from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import get_db, SessionLocal
from app.models import Trip, TripMember, User, VenueMetadata, ChatMessage
from app.schemas import AIAskRequest, AIAskResponse
from app.security import current_user, get_room_role
from app.concierge.rag import execute_concierge_query
from app.concierge.constraints import VenueCandidate
from app.realtime.manager import manager
from app.realtime.handlers import log_event

router = APIRouter(prefix="/api/v1/trips", tags=["AI Concierge"])


@router.post("/{trip_id}/ai/ask", response_model=AIAskResponse)
async def ask_ai_concierge(
    trip_id: int,
    req: AIAskRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify room membership
    await get_room_role(user, trip_id, db)

    # 1. Query trip & attendees
    trip = await db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    members_stmt = (
        select(TripMember, User)
        .join(User, TripMember.user_id == User.id)
        .where(TripMember.trip_id == trip_id)
    )
    members_res = await db.execute(members_stmt)
    members_data = members_res.all()

    # Collect union of dietary tags and min budget ceiling
    all_dietary = set()
    budget_ceilings = []
    for tm, u in members_data:
        all_dietary.update(u.dietary_tags or [])
        budget_ceilings.append(u.budget_ceiling)

    min_ceiling = min(budget_ceilings) if budget_ceilings else 150.0

    # 2. Query all venues for this destination
    venues_stmt = (
        select(VenueMetadata)
        .where(VenueMetadata.destination.ilike(trip.destination))
        .options(selectinload(VenueMetadata.dietary_tags))
    )
    venues_res = await db.execute(venues_stmt)
    venues_db = venues_res.scalars().all()

    # Dynamically seed if this is a newly targeted global destination
    if not venues_db:
        from app.destinations import resolve_country_and_currency, generate_local_places_for_destination
        resolved_c, resolved_d, curr, sym, b_lat, b_lng = resolve_country_and_currency(trip.country, trip.destination)
        gen_places = generate_local_places_for_destination(resolved_d, resolved_c, curr, sym, b_lat, b_lng)
        for gp in gen_places:
            v_obj = VenueMetadata(
                id=gp["venueId"],
                name=gp["name"],
                category=gp["category"],
                price_per_person=float(gp["pricePerPerson"]),
                destination=resolved_d,
                country=resolved_c,
                currency=curr,
                lat=float(gp["coordinates"]["lat"]),
                lng=float(gp["coordinates"]["lng"]),
                rating=float(gp["rating"]),
                open_time=gp["hours"]["open"],
                close_time=gp["hours"]["close"],
                open_min=int(gp["hours"]["open"].split(":")[0]) * 60 + int(gp["hours"]["open"].split(":")[1]),
                close_min=int(gp["hours"]["close"].split(":")[0]) * 60 + int(gp["hours"]["close"].split(":")[1]),
                description=gp.get("description", "")
            )
            db.add(v_obj)
        await db.commit()
        # Re-query
        re_res = await db.execute(venues_stmt)
        venues_db = re_res.scalars().all()

    candidates = [
        VenueCandidate(
            id=v.id,
            name=v.name,
            category=v.category,
            price_per_person=v.price_per_person,
            dietary_tags=[t.tag for t in v.dietary_tags],
            open_min=v.open_min,
            close_min=v.close_min,
            lat=v.lat,
            lng=v.lng,
            rating=v.rating,
            description=v.description or ""
        )
        for v in venues_db
    ]

    # Anchor coordinates if anchor_venue_id is provided
    anchor_coords = None
    if req.anchor_venue_id:
        anchor_v = await db.get(VenueMetadata, req.anchor_venue_id)
        if anchor_v:
            anchor_coords = (anchor_v.lat, anchor_v.lng)

    # 3. Execute Concierge RAG pipeline
    result = await execute_concierge_query(
        question=req.question,
        all_venues=candidates,
        travelers_dietary=frozenset(all_dietary),
        travelers_min_ceiling=float(min_ceiling),
        anchor_coords=anchor_coords,
        currency_symbol=trip.currency_symbol or "€",
        destination=trip.destination
    )

    # 4. Persist AI answer in chat
    ai_msg = ChatMessage(
        trip_id=trip_id,
        user_id=None,
        user_name="AI Concierge",
        message_type="ai_answer",
        content=result["answer"]
    )
    db.add(ai_msg)
    await db.commit()
    await db.refresh(ai_msg)

    # 5. Broadcast suggestion and log event
    await log_event(trip_id, user.id, "ai.asked", {
        "question": req.question,
        "answer": result["answer"],
        "suggestedVenueId": result["suggestedVenueId"],
        "latencyMs": result["latencyMs"]
    })

    await manager.broadcast(trip_id, "trip.ai.suggestion", {
        "question": req.question,
        "answer": result["answer"],
        "suggestedVenueId": result["suggestedVenueId"],
        "sourceEvents": result["sourceEvents"],
        "generatedAt": result["generatedAt"],
        "latencyMs": result["latencyMs"]
    })

    return AIAskResponse(
        answer=result["answer"],
        suggestedVenueId=result["suggestedVenueId"],
        sourceEvents=result["sourceEvents"],
        generatedAt=result["generatedAt"],
        latencyMs=result["latencyMs"]
    )

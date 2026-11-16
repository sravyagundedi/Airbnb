import datetime
from typing import List, Optional, Dict, Any
from math import cos, radians
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models import VenueMetadata, VenueDietaryTag, SavedVenue, User
from app.schemas import VenueResponse, HoursDict, CoordinatesDict, SavedVenueResponse
from app.security import current_user
from app.concierge.constraints import haversine_km
from app.destinations import COUNTRY_DIRECTORY, resolve_country_and_currency, generate_local_places_for_destination


router = APIRouter(tags=["Venues"])


def format_venue(v: VenueMetadata, tags: List[str]) -> VenueResponse:
    return VenueResponse(
        venueId=v.id,
        name=v.name,
        category=v.category,
        destination=v.destination or "Lisbon",
        country=v.country or "Portugal",
        currency=v.currency or "EUR",
        pricePerPerson=v.price_per_person,
        dietaryTags=tags,
        hours=HoursDict(open=v.open_time, close=v.close_time),
        coordinates=CoordinatesDict(lat=v.lat, lng=v.lng),
        rating=v.rating,
        description=v.description or ""
    )


@router.get("/api/v1/destinations/countries")
async def list_countries():
    """Returns directory of countries with flags, currencies, symbols, and default cities."""
    countries_list = []
    for name, data in COUNTRY_DIRECTORY.items():
        countries_list.append({
            "country": name,
            "flag": data["flag"],
            "currency": data["currency"],
            "symbol": data["symbol"],
            "defaultCity": data["default_city"],
            "cities": data["cities"]
        })
    return countries_list


@router.get("/api/v1/destinations/{destination}/venues", response_model=List[VenueResponse])
async def get_destination_venues(
    destination: str,
    country: Optional[str] = Query(None, description="Optional country name for disambiguation"),
    near: Optional[str] = Query(None, description="Anchor coordinates as 'lat,lng' e.g. '38.7139,-9.1394'"),
    radiusKm: Optional[float] = Query(None, description="Filter radius in kilometers e.g. 2.0"),
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(VenueMetadata)
        .where(VenueMetadata.destination.ilike(destination.strip()))
        .options(selectinload(VenueMetadata.dietary_tags))
    )

    if category:
        stmt = stmt.where(VenueMetadata.category == category.lower())

    anchor_coords = None
    if near:
        try:
            parts = near.split(",")
            lat, lng = float(parts[0].strip()), float(parts[1].strip())
            anchor_coords = (lat, lng)

            # SQL Bounding Box pre-filter (1 deg lat ~= 111 km)
            rad = radiusKm or 10.0
            lat_delta = rad / 111.0
            lng_delta = rad / (111.0 * max(0.1, cos(radians(lat))))

            stmt = stmt.where(
                VenueMetadata.lat.between(lat - lat_delta, lat + lat_delta),
                VenueMetadata.lng.between(lng - lng_delta, lng + lng_delta)
            )
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid 'near' coordinate format. Expected 'lat,lng'")

    result = await db.execute(stmt)
    venues = result.scalars().all()

    # If no venues exist for this destination, dynamically generate authentic local places
    # calibrated with country-specific currency and coordinates
    if not venues and not category and not near:
        resolved_country, resolved_dest, currency, symbol, base_lat, base_lng = resolve_country_and_currency(
            country=country,
            destination=destination
        )
        generated = generate_local_places_for_destination(
            destination=resolved_dest,
            country=resolved_country,
            currency=currency,
            symbol=symbol,
            base_lat=base_lat,
            base_lng=base_lng
        )

        for item in generated:
            vid = item["venueId"]
            existing = await db.get(VenueMetadata, vid)
            if existing:
                continue
            v = VenueMetadata(
                id=vid,
                name=item["name"],
                category=item["category"],
                price_per_person=float(item["pricePerPerson"]),
                destination=resolved_dest,
                country=resolved_country,
                currency=currency,
                lat=float(item["coordinates"]["lat"]),
                lng=float(item["coordinates"]["lng"]),
                rating=float(item["rating"]),
                open_time=item["hours"]["open"],
                close_time=item["hours"]["close"],
                open_min=int(item["hours"]["open"].split(":")[0]) * 60 + int(item["hours"]["open"].split(":")[1]),
                close_min=int(item["hours"]["close"].split(":")[0]) * 60 + int(item["hours"]["close"].split(":")[1]),
                description=item.get("description", "")
            )
            db.add(v)
            for tag in item.get("dietaryTags", []):
                db.add(VenueDietaryTag(venue_id=vid, tag=tag.lower()))

        await db.commit()

        # Re-query
        re_result = await db.execute(
            select(VenueMetadata)
            .where(VenueMetadata.destination.ilike(destination.strip()))
            .options(selectinload(VenueMetadata.dietary_tags))
        )
        venues = re_result.scalars().all()

    out = []
    for v in venues:
        tags = [t.tag for t in v.dietary_tags]
        if anchor_coords and radiusKm is not None:
            # Exact Haversine filter in Python
            dist = haversine_km(anchor_coords, (v.lat, v.lng))
            if dist > radiusKm:
                continue
        out.append(format_venue(v, tags))

    return out


@router.get("/api/v1/venues", response_model=List[VenueResponse])
async def list_all_venues(db: AsyncSession = Depends(get_db)):
    stmt = select(VenueMetadata).options(selectinload(VenueMetadata.dietary_tags))
    result = await db.execute(stmt)
    venues = result.scalars().all()
    return [format_venue(v, [t.tag for t in v.dietary_tags]) for v in venues]


@router.post("/api/v1/venues/{venue_id}/save", response_model=SavedVenueResponse)
async def toggle_save_venue(
    venue_id: str,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db)
):
    venue = await db.get(VenueMetadata, venue_id)
    if not venue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venue not found")

    stmt = select(SavedVenue).where(SavedVenue.user_id == user.id, SavedVenue.venue_id == venue_id)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        # Already saved, return existing
        sv = existing
    else:
        sv = SavedVenue(
            user_id=user.id,
            venue_id=venue_id,
            created_at=datetime.datetime.utcnow()
        )
        db.add(sv)
        await db.commit()
        await db.refresh(sv)

    # Fetch tags
    tag_stmt = select(VenueDietaryTag.tag).where(VenueDietaryTag.venue_id == venue_id)
    tags = (await db.execute(tag_stmt)).scalars().all()

    return SavedVenueResponse(
        id=sv.id,
        venue_id=venue.id,
        name=venue.name,
        category=venue.category,
        price_per_person=venue.price_per_person,
        rating=venue.rating,
        dietary_tags=tags,
        notes=sv.notes,
        saved_at=sv.created_at
    )


@router.delete("/api/v1/venues/{venue_id}/save")
async def unsave_venue(
    venue_id: str,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = delete(SavedVenue).where(SavedVenue.user_id == user.id, SavedVenue.venue_id == venue_id)
    await db.execute(stmt)
    await db.commit()
    return {"message": "Venue removed from saved places"}


@router.get("/api/v1/venues/saved", response_model=List[SavedVenueResponse])
async def list_saved_venues(
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(SavedVenue, VenueMetadata)
        .join(VenueMetadata, SavedVenue.venue_id == VenueMetadata.id)
        .where(SavedVenue.user_id == user.id)
        .order_by(SavedVenue.created_at.desc())
    )
    results = (await db.execute(stmt)).all()

    out = []
    for sv, venue in results:
        tag_stmt = select(VenueDietaryTag.tag).where(VenueDietaryTag.venue_id == venue.id)
        tags = (await db.execute(tag_stmt)).scalars().all()
        out.append(SavedVenueResponse(
            id=sv.id,
            venue_id=venue.id,
            name=venue.name,
            category=venue.category,
            price_per_person=venue.price_per_person,
            rating=venue.rating,
            dietary_tags=tags,
            notes=sv.notes,
            saved_at=sv.created_at
        ))
    return out


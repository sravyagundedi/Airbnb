from typing import List, Optional
from math import cos, radians
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models import VenueMetadata, VenueDietaryTag
from app.schemas import VenueResponse, HoursDict, CoordinatesDict
from app.concierge.constraints import haversine_km

router = APIRouter(tags=["Venues"])


def format_venue(v: VenueMetadata, tags: List[str]) -> VenueResponse:
    return VenueResponse(
        venueId=v.id,
        name=v.name,
        category=v.category,
        pricePerPerson=v.price_per_person,
        dietaryTags=tags,
        hours=HoursDict(open=v.open_time, close=v.close_time),
        coordinates=CoordinatesDict(lat=v.lat, lng=v.lng),
        rating=v.rating,
        description=v.description or ""
    )


@router.get("/api/v1/destinations/{destination}/venues", response_model=List[VenueResponse])
async def get_destination_venues(
    destination: str,
    near: Optional[str] = Query(None, description="Anchor coordinates as 'lat,lng' e.g. '38.7139,-9.1394'"),
    radiusKm: Optional[float] = Query(None, description="Filter radius in kilometers e.g. 2.0"),
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(VenueMetadata)
        .where(VenueMetadata.destination.ilike(destination))
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

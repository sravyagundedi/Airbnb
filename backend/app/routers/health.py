import time
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models import VenueMetadata
from app.schemas import VenueResponse
from app.routers.venues import format_venue
from app.realtime.manager import manager
from app.reco.serve import recommender_service
from app.security import current_user
from app.models import User

router = APIRouter(tags=["Health & Recommendations"])


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "warroom-api",
        "timestamp": int(time.time() * 1000)
    }


@router.get("/health/ws")
async def health_ws():
    active_rooms = len(manager.rooms)
    total_connections = sum(len(clients) for clients in manager.rooms.values())
    return {
        "gatewayStatus": "online",
        "activeRooms": active_rooms,
        "totalConnections": total_connections,
        "frozenRooms": [rid for rid, frozen in manager.frozen_rooms.items() if frozen],
        "activeVotes": list(manager.active_votes.keys())
    }


@router.get("/api/v1/recommendations", response_model=List[VenueResponse])
async def get_recommendations(
    user_id: Optional[int] = Query(None),
    top_k: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db)
):
    rec_ids = recommender_service.recommend(user_id=user_id, top_k=top_k)
    
    if not rec_ids:
        # Fallback to top-rated Lisbon venues
        stmt = select(VenueMetadata).order_by(VenueMetadata.rating.desc()).limit(top_k).options(selectinload(VenueMetadata.dietary_tags))
        result = await db.execute(stmt)
        venues = result.scalars().all()
        return [format_venue(v, [t.tag for t in v.dietary_tags]) for v in venues]

    # Query venues in ranked order
    stmt = (
        select(VenueMetadata)
        .where(VenueMetadata.id.in_(rec_ids))
        .options(selectinload(VenueMetadata.dietary_tags))
    )
    result = await db.execute(stmt)
    venues_map = {v.id: v for v in result.scalars().all()}

    ordered_venues = []
    for vid in rec_ids:
        if vid in venues_map:
            v = venues_map[vid]
            ordered_venues.append(format_venue(v, [t.tag for t in v.dietary_tags]))

    return ordered_venues

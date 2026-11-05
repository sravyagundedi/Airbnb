from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.db import get_db
from app.models import VenueMetadata, VenueDietaryTag, User
from app.schemas import AdminVenueRow
from app.security import require_role
from app.reco.train import train_and_evaluate
from app.reco.serve import recommender_service
from scripts.gen_interactions import generate_synthetic_data
import os
import json

router = APIRouter(prefix="/api/v1/admin", tags=["Admin Operations"])


def time_to_min(t: str) -> int:
    h, m = map(int, t.split(":"))
    return h * 60 + m


@router.post("/destinations/{destination}/venues", status_code=status.HTTP_201_CREATED)
async def upload_venues_dataset(
    destination: str,
    raw_venues: List[Dict[str, Any]],
    admin_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
):
    """
    Validates and uploads venue batch.
    Rejects the entire file if ANY row fails validation, returning row-indexed error list.
    Wraps entire insertion in a single atomic database transaction.
    """
    row_errors = []
    validated_rows: List[AdminVenueRow] = []

    for idx, item in enumerate(raw_venues):
        try:
            validated = AdminVenueRow(**item)
            validated_rows.append(validated)
        except Exception as e:
            row_errors.append({
                "row": idx + 1,
                "venueId": item.get("venueId", f"row_{idx+1}"),
                "errors": [str(err) for err in (e.errors() if hasattr(e, "errors") else [e])]
            })

    if row_errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": f"Validation failed for {len(row_errors)} out of {len(raw_venues)} rows. Transaction rolled back.",
                "rowErrors": row_errors
            }
        )

    # Perform atomic insertion / update inside transaction
    try:
        for v in validated_rows:
            open_m = time_to_min(v.hours.open)
            close_m = time_to_min(v.hours.close)

            existing = await db.get(VenueMetadata, v.venueId)
            if existing:
                existing.name = v.name
                existing.category = v.category
                existing.price_per_person = v.pricePerPerson
                existing.destination = destination
                existing.lat = v.coordinates.lat
                existing.lng = v.coordinates.lng
                existing.rating = v.rating
                existing.open_time = v.hours.open
                existing.close_time = v.hours.close
                existing.open_min = open_m
                existing.close_min = close_m
                existing.description = v.description or ""
            else:
                db_venue = VenueMetadata(
                    id=v.venueId,
                    name=v.name,
                    category=v.category,
                    price_per_person=v.pricePerPerson,
                    destination=destination,
                    lat=v.coordinates.lat,
                    lng=v.coordinates.lng,
                    rating=v.rating,
                    open_time=v.hours.open,
                    close_time=v.hours.close,
                    open_min=open_m,
                    close_min=close_m,
                    description=v.description or ""
                )
                db.add(db_venue)

            await db.flush()

            # Synchronize dietary tags
            await db.execute(delete(VenueDietaryTag).where(VenueDietaryTag.venue_id == v.venueId))
            for tag in v.dietaryTags:
                db.add(VenueDietaryTag(venue_id=v.venueId, tag=tag))

        await db.commit()
    except Exception as e:
        import logging
        logging.getLogger("warroom.admin").error(f"Admin upload transaction failed: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database transaction error: {str(e)}"
        )

    return {
        "status": "success",
        "destination": destination,
        "venuesProcessed": len(validated_rows)
    }


@router.post("/reco/retrain")
async def trigger_reco_retrain(
    admin_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
):
    """Triggers recommendation model retraining."""
    venues_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "lisbon_venues.json")
    inter_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "synthetic_interactions.json")

    if not os.path.exists(inter_path):
        generate_synthetic_data()

    with open(venues_path, "r", encoding="utf-8") as f:
        venues = json.load(f)
    with open(inter_path, "r", encoding="utf-8") as f:
        interactions = json.load(f)

    p_at_5 = train_and_evaluate(interactions, venues)
    recommender_service.load_artifacts()

    return {
        "status": "success",
        "precisionAt5": round(p_at_5, 4),
        "artifactsReloaded": recommender_service.loaded
    }

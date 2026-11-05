import asyncio
import json
import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db import SessionLocal, init_db
from app.models import VenueMetadata, VenueDietaryTag
from sqlalchemy import select, delete


def time_to_min(time_str: str) -> int:
    parts = time_str.split(":")
    return int(parts[0]) * 60 + int(parts[1])


async def seed_venues():
    print("Initializing database schema...")
    await init_db()

    data_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "lisbon_venues.json")
    with open(data_path, "r", encoding="utf-8") as f:
        venues_data = json.load(f)

    async with SessionLocal() as db:
        print(f"Seeding {len(venues_data)} Lisbon venues into database...")
        for item in venues_data:
            vid = item["venueId"]
            open_str = item["hours"]["open"]
            close_str = item["hours"]["close"]
            open_m = time_to_min(open_str)
            close_m = time_to_min(close_str)

            existing = await db.get(VenueMetadata, vid)
            if existing:
                existing.name = item["name"]
                existing.category = item["category"]
                existing.price_per_person = float(item["pricePerPerson"])
                existing.lat = float(item["coordinates"]["lat"])
                existing.lng = float(item["coordinates"]["lng"])
                existing.rating = float(item["rating"])
                existing.open_time = open_str
                existing.close_time = close_str
                existing.open_min = open_m
                existing.close_min = close_m
                existing.description = item.get("description", "")
            else:
                venue = VenueMetadata(
                    id=vid,
                    name=item["name"],
                    category=item["category"],
                    price_per_person=float(item["pricePerPerson"]),
                    destination="Lisbon",
                    lat=float(item["coordinates"]["lat"]),
                    lng=float(item["coordinates"]["lng"]),
                    rating=float(item["rating"]),
                    open_time=open_str,
                    close_time=close_str,
                    open_min=open_m,
                    close_min=close_m,
                    description=item.get("description", "")
                )
                db.add(venue)

            # Update dietary tags
            await db.execute(delete(VenueDietaryTag).where(VenueDietaryTag.venue_id == vid))
            for tag in item.get("dietaryTags", []):
                dtag = VenueDietaryTag(venue_id=vid, tag=tag.lower())
                db.add(dtag)

        await db.commit()
        print(f"Successfully seeded {len(venues_data)} venues.")


if __name__ == "__main__":
    asyncio.run(seed_venues())

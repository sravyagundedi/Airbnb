import json
import random
import os
import asyncio
from app.db import SessionLocal, init_db
from app.models import Interaction, VenueMetadata, User


PERSONAS = {
    "budget_foodie": {
        "categories": ["lunch", "dinner"],
        "max_price": 25,
        "tags": [],
        "weight": 1.2
    },
    "vegetarian": {
        "categories": ["lunch", "breakfast", "dinner"],
        "max_price": 45,
        "tags": ["vegetarian", "vegan"],
        "weight": 1.3
    },
    "culture": {
        "categories": ["activity", "transit"],
        "max_price": 40,
        "tags": [],
        "weight": 1.1
    },
    "nightlife": {
        "categories": ["nightlife", "dinner"],
        "max_price": 50,
        "tags": [],
        "weight": 1.2
    },
    "family": {
        "categories": ["activity", "breakfast", "lodging"],
        "max_price": 60,
        "tags": ["vegetarian"],
        "weight": 1.0
    }
}


def generate_synthetic_data(num_users: int = 200):
    venues_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "lisbon_venues.json")
    with open(venues_path, "r", encoding="utf-8") as f:
        venues = json.load(f)

    users = []
    interactions = []
    persona_names = list(PERSONAS.keys())

    # Create 40 co-travel groups of ~5 users each
    groups = []
    for g in range(40):
        group_persona = random.choice(persona_names)
        groups.append([g * 5 + i + 1 for i in range(5)])

    for uid in range(1, num_users + 1):
        # Assign persona (aligned with co-travel group)
        group_id = (uid - 1) // 5
        persona_name = persona_names[group_id % len(persona_names)]
        persona = PERSONAS[persona_name]

        users.append({
            "id": uid,
            "email": f"traveler_{uid}@example.com",
            "displayName": f"Traveler {uid}",
            "persona": persona_name,
            "groupId": group_id
        })

        # Calculate venue affinities
        scored_venues = []
        for v in venues:
            affinity = 0.1  # base noise
            if v["category"] in persona["categories"]:
                affinity += 0.5
            if v["pricePerPerson"] <= persona["max_price"]:
                affinity += 0.3
            if any(t in persona["tags"] for t in v.get("dietaryTags", [])):
                affinity += 0.4
            
            # Co-travel common anchor effect
            if (hash(v["venueId"]) + group_id) % 7 == 0:
                affinity += 0.4

            scored_venues.append((v["venueId"], affinity))

        # Sample ~20 interactions per user
        weights = [max(0.01, score) for _, score in scored_venues]
        total_w = sum(weights)
        probs = [w / total_w for w in weights]
        
        # Pick 20 distinct venues
        chosen_indices = set()
        attempts = 0
        while len(chosen_indices) < 20 and attempts < 100:
            attempts += 1
            idx = random.choices(range(len(venues)), weights=probs, k=1)[0]
            chosen_indices.add(idx)

        for idx in chosen_indices:
            v = venues[idx]
            # Liked or viewed
            itype = "like" if random.random() < 0.75 else "view"
            weight = 2.0 if itype == "like" else 1.0
            interactions.append({
                "userId": uid,
                "venueId": v["venueId"],
                "interactionType": itype,
                "weight": weight
            })

    output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    out_file = os.path.join(output_dir, "synthetic_interactions.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"users": users, "interactions": interactions}, f, indent=2)

    print(f"Generated {len(users)} users and {len(interactions)} synthetic interactions saved to {out_file}")
    return users, interactions


if __name__ == "__main__":
    generate_synthetic_data()

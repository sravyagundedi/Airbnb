import re
import json
import time
import httpx
from typing import Dict, List, Any, Optional, Tuple
from app.config import settings
from app.concierge.constraints import (
    Req, VenueCandidate, rank, diagnose_elimination
)

# Regex patterns for fast deterministic extraction
PRICE_REGEX = re.compile(r"(?:under|less than|max|budget of|within)\s*\$?(\d+(?:\.\d+)?)", re.IGNORECASE)
CATEGORY_MAP = {
    "dinner": ["dinner", "supper", "evening meal", "dine"],
    "lunch": ["lunch", "midday"],
    "breakfast": ["breakfast", "brunch", "morning", "coffee", "pastry"],
    "nightlife": ["bar", "drinks", "rooftop", "pub", "cocktail", "nightlife", "party"],
    "activity": ["activity", "museum", "tour", "walk", "visit", "sightseeing", "palace", "castle"],
    "transit": ["tram", "transit", "metro", "bus", "ferry"],
    "lodging": ["hotel", "hostel", "stay", "sleep", "lodging"]
}


def parse_question_to_req(
    question: str,
    travelers_dietary: frozenset,
    travelers_min_ceiling: float,
    anchor_coords: Optional[Tuple[float, float]] = None,
    default_start_min: int = 1140,  # 19:00
    default_end_min: int = 1260,    # 21:00
) -> Req:
    q_lower = question.lower()

    # 1. Price ceiling from question (overrides traveler min ceiling if explicitly stated)
    price_match = PRICE_REGEX.search(question)
    if price_match:
        ceiling = float(price_match.group(1))
    else:
        ceiling = travelers_min_ceiling

    # 2. Category matching
    detected_cat = "dinner"  # default
    for cat, keywords in CATEGORY_MAP.items():
        if any(kw in q_lower for kw in keywords):
            detected_cat = cat
            break

    # Adjust default slot based on category if not explicitly given
    slot_start = default_start_min
    slot_end = default_end_min
    if detected_cat == "breakfast":
        slot_start, slot_end = 540, 630   # 09:00 - 10:30
    elif detected_cat == "lunch":
        slot_start, slot_end = 750, 840   # 12:30 - 14:00
    elif detected_cat == "nightlife":
        slot_start, slot_end = 1260, 1380 # 21:00 - 23:00
    elif detected_cat == "activity":
        slot_start, slot_end = 600, 780   # 10:00 - 13:00

    # Dietary: check if query specifies additional dietary preference
    dietary_needed = set(travelers_dietary)
    if "vegan" in q_lower:
        dietary_needed.add("vegan")
    if "vegetarian" in q_lower or "veggie" in q_lower:
        dietary_needed.add("vegetarian")
    if "halal" in q_lower:
        dietary_needed.add("halal")
    if "gluten" in q_lower or "gluten-free" in q_lower:
        dietary_needed.add("gluten-free")

    return Req(
        category=detected_cat,
        ceiling=ceiling,
        dietary=frozenset(dietary_needed),
        slot_start=slot_start,
        slot_end=slot_end,
        anchor=anchor_coords,
        radius_km=2.0,
        buffer_min=30
    )


async def call_llm_or_fallback(
    candidates: List[VenueCandidate],
    question: str,
    currency_symbol: str = "€",
    destination: str = "Lisbon"
) -> Tuple[Optional[str], str]:
    """
    Calls LLM with candidates and question, with 2.5s strict timeout.
    Falls back gracefully to deterministic grounded template on error/timeout/mock.
    """
    if not candidates:
        return (None, "No candidates found.")

    top_choice = candidates[0]
    price_formatted = (
        f"{currency_symbol}{top_choice.price_per_person:,.0f}"
        if currency_symbol in ["¥", "₩", "₹"]
        else f"{currency_symbol}{top_choice.price_per_person:.2f}"
    )
    fallback_answer = (
        f"Based on your requirements, I recommend {top_choice.name} ({top_choice.category}). "
        f"It costs approximately {price_formatted} per person and holds a "
        f"{top_choice.rating}★ rating. {top_choice.description}"
    )

    # If mock key or invalid key, return template immediately
    if not settings.LLM_API_KEY or settings.LLM_API_KEY.startswith("mock-"):
        return (top_choice.id, fallback_answer)

    candidates_summary = [
        {
            "venueId": c.id,
            "name": c.name,
            "category": c.category,
            "price": c.price_per_person,
            "rating": c.rating,
            "dietary": c.dietary_tags,
            "description": c.description
        }
        for c in candidates[:3]
    ]

    prompt = (
        f"Question: {question}\n\n"
        f"Available candidate venues:\n{json.dumps(candidates_summary, indent=2)}\n\n"
        "Instructions: Select the best venue from the candidate list that addresses the question. "
        "Never invent prices, hours, or details. Return ONLY valid JSON in format: "
        "{\"venueId\": \"<id>\", \"answer\": \"<concise helpful explanation citing the venue>\"}"
    )

    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            headers = {
                "Authorization": f"Bearer {settings.LLM_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": settings.LLM_MODEL,
                "messages": [
                    {"role": "system", "content": f"You are the AI Concierge for {destination} group trip planning."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"}
            }
            resp = await client.post(
                f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                v_id = parsed.get("venueId")
                ans = parsed.get("answer", fallback_answer)
                return (v_id, ans)
    except Exception:
        pass  # Fall back to deterministic template on any timeout or network error

    return (top_choice.id, fallback_answer)


async def execute_concierge_query(
    question: str,
    all_venues: List[VenueCandidate],
    travelers_dietary: frozenset,
    travelers_min_ceiling: float,
    anchor_coords: Optional[Tuple[float, float]] = None,
    currency_symbol: str = "€",
    destination: str = "Lisbon"
) -> Dict[str, Any]:
    t0 = time.perf_counter()

    # 1. Parse question to structured requirement
    req = parse_question_to_req(
        question=question,
        travelers_dietary=travelers_dietary,
        travelers_min_ceiling=travelers_min_ceiling,
        anchor_coords=anchor_coords
    )

    # 2. Hard deterministic filter & rank
    ranked_candidates = rank(all_venues, req)
    top_candidates = ranked_candidates[:5]

    t_filtered = time.perf_counter()

    # 3. Honest hedge if no candidates match
    if not top_candidates:
        elimination_counts = diagnose_elimination(all_venues, req)
        # Find the constraint that eliminated the most venues
        eliminators = {k: v for k, v in elimination_counts.items() if k != "category_mismatch" and v > 0}
        if eliminators:
            worst_constraint, count = max(eliminators.items(), key=lambda x: x[1])
            hedge_msg = (
                f"No venue in the {destination} dataset satisfies all group constraints for {req.category}. "
                f"The '{worst_constraint}' rule eliminated {count} candidate(s). "
                f"Consider relaxing your {worst_constraint} constraint (current budget ceiling: {currency_symbol}{req.ceiling}, "
                f"dietary: {list(req.dietary)}, radius: {req.radius_km} km)."
            )
        else:
            hedge_msg = (
                f"No venue in the dataset matched category '{req.category}'. "
                "Consider searching for dinner, lunch, breakfast, activity, or nightlife."
            )

        total_ms = (time.perf_counter() - t0) * 1000
        return {
            "answer": hedge_msg,
            "suggestedVenueId": None,
            "sourceEvents": [],
            "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "latencyMs": round(total_ms, 2)
        }

    # 4. Generate answer via LLM or template
    suggested_id, raw_answer = await call_llm_or_fallback(
        top_candidates,
        question,
        currency_symbol=currency_symbol,
        destination=destination
    )

    # 5. Code-side validation
    valid_ids = {c.id for c in top_candidates}
    venue_map = {c.id: c for c in top_candidates}

    price_str = (
        f"{currency_symbol}{top_candidates[0].price_per_person:,.0f}"
        if currency_symbol in ["¥", "₩", "₹"]
        else f"{currency_symbol}{top_candidates[0].price_per_person:.2f}"
    )

    if suggested_id not in valid_ids:
        # Hallucinated or invalid ID discarded; substitute top ranked candidate
        suggested_id = top_candidates[0].id
        chosen_venue = top_candidates[0]
        raw_answer = (
            f"I recommend {chosen_venue.name} in {destination}. "
            f"It fits your group's budget at {price_str}/person with a "
            f"{chosen_venue.rating}★ rating. {chosen_venue.description}"
        )

    chosen_venue = venue_map[suggested_id]
    venue_price_str = (
        f"{currency_symbol}{chosen_venue.price_per_person:,.0f}"
        if currency_symbol in ["¥", "₩", "₹"]
        else f"{currency_symbol}{chosen_venue.price_per_person:.2f}"
    )

    # Enforce correct DB price in text (replace hallucinated prices)
    verified_answer = re.sub(
        r"(?:€|\$|£|¥|₹)\s*\d+(?:\.\d+)?",
        venue_price_str,
        raw_answer
    )

    total_ms = (time.perf_counter() - t0) * 1000
    return {
        "answer": verified_answer,
        "suggestedVenueId": suggested_id,
        "sourceEvents": [f"venue_{suggested_id}"],
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "latencyMs": round(total_ms, 2)
    }

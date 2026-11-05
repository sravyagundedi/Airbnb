import pytest
from app.destinations import COUNTRY_DIRECTORY, resolve_country_and_currency, generate_local_places_for_destination
from app.concierge.rag import execute_concierge_query
from app.concierge.constraints import VenueCandidate


def test_country_directory_coverage():
    assert "Portugal" in COUNTRY_DIRECTORY
    assert "Japan" in COUNTRY_DIRECTORY
    assert "France" in COUNTRY_DIRECTORY
    assert "United States" in COUNTRY_DIRECTORY
    assert "India" in COUNTRY_DIRECTORY
    assert "United Arab Emirates" in COUNTRY_DIRECTORY

    assert COUNTRY_DIRECTORY["Japan"]["currency"] == "JPY"
    assert COUNTRY_DIRECTORY["Japan"]["symbol"] == "¥"
    assert COUNTRY_DIRECTORY["United States"]["currency"] == "USD"
    assert COUNTRY_DIRECTORY["United States"]["symbol"] == "$"
    assert COUNTRY_DIRECTORY["India"]["currency"] == "INR"
    assert COUNTRY_DIRECTORY["India"]["symbol"] == "₹"


def test_resolve_country_and_currency():
    # 1. Direct country match
    c, dest, curr, sym, lat, lng = resolve_country_and_currency("Japan", "Tokyo")
    assert c == "Japan"
    assert dest == "Tokyo"
    assert curr == "JPY"
    assert sym == "¥"

    # 2. City match when country omitted
    c2, dest2, curr2, sym2, _, _ = resolve_country_and_currency(None, "Paris")
    assert c2 == "France"
    assert dest2 == "Paris"
    assert curr2 == "EUR"
    assert sym2 == "€"

    # 3. Custom / fallback destination anywhere in the world
    c3, dest3, curr3, sym3, _, _ = resolve_country_and_currency("Iceland", "Reykjavik")
    assert c3 == "Iceland"
    assert dest3 == "Reykjavik"
    assert curr3 == "USD"  # fallback default
    assert sym3 == "$"


def test_generate_local_places_for_any_destination():
    places = generate_local_places_for_destination(
        destination="Kyoto",
        country="Japan",
        currency="JPY",
        symbol="¥",
        base_lat=35.0116,
        base_lng=135.7681
    )
    assert len(places) >= 6
    categories = {p["category"] for p in places}
    assert "dinner" in categories
    assert "lunch" in categories
    assert "activity" in categories

    # Verify JPY currency multiplier calibration (e.g. prices in thousands of yen)
    for p in places:
        assert p["pricePerPerson"] >= 1000  # realistic Japanese Yen pricing


@pytest.mark.asyncio
async def test_ai_concierge_with_dynamic_destination_and_currency():
    # Generate Tokyo candidates
    raw_places = generate_local_places_for_destination(
        destination="Tokyo",
        country="Japan",
        currency="JPY",
        symbol="¥",
        base_lat=35.6762,
        base_lng=139.6503
    )

    candidates = [
        VenueCandidate(
            id=p["venueId"],
            name=p["name"],
            category=p["category"],
            price_per_person=p["pricePerPerson"],
            dietary_tags=p["dietaryTags"],
            open_min=int(p["hours"]["open"].split(":")[0]) * 60 + int(p["hours"]["open"].split(":")[1]),
            close_min=int(p["hours"]["close"].split(":")[0]) * 60 + int(p["hours"]["close"].split(":")[1]),
            lat=p["coordinates"]["lat"],
            lng=p["coordinates"]["lng"],
            rating=p["rating"],
            description=p["description"]
        )
        for p in raw_places
    ]

    res = await execute_concierge_query(
        question="Where can we have traditional dinner in Tokyo?",
        all_venues=candidates,
        travelers_dietary=frozenset(),
        travelers_min_ceiling=10000.0,
        currency_symbol="¥",
        destination="Tokyo"
    )

    assert res["suggestedVenueId"] is not None
    assert "¥" in res["answer"]
    assert len(res["sourceEvents"]) > 0

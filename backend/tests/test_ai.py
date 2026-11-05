import pytest
from app.concierge.rag import execute_concierge_query, call_llm_or_fallback
from app.concierge.constraints import VenueCandidate

LISBON_ANCHOR = (38.7139, -9.1394)


def make_venue(id, name, cat, price, tags, rating=4.5):
    return VenueCandidate(
        id=id,
        name=name,
        category=cat,
        price_per_person=price,
        dietary_tags=tags,
        open_min=540,
        close_min=1400,
        lat=LISBON_ANCHOR[0],
        lng=LISBON_ANCHOR[1],
        rating=rating,
        description="Authentic Lisbon venue."
    )


@pytest.mark.asyncio
async def test_ai_grounded_citation_present():
    venues = [
        make_venue("v_3391", "Taberna da Rua", "dinner", 22.0, ["vegetarian"], rating=4.8),
        make_venue("v_3392", "Prado", "dinner", 45.0, ["gluten-free"], rating=4.7),
    ]

    res = await execute_concierge_query(
        question="Where can we have a vegetarian dinner under $30?",
        all_venues=venues,
        travelers_dietary=frozenset(),
        travelers_min_ceiling=50.0,
        anchor_coords=LISBON_ANCHOR
    )

    assert res["suggestedVenueId"] == "v_3391"
    assert "venue_v_3391" in res["sourceEvents"]
    assert "Taberna da Rua" in res["answer"]
    assert "€22.00" in res["answer"]  # Price verified from DB


@pytest.mark.asyncio
async def test_ai_honest_hedge_when_no_candidates():
    # Only expensive venues (> €100)
    venues = [
        make_venue("v_3393", "Belcanto", "dinner", 195.0, ["gluten-free"]),
        make_venue("v_3394", "Alma", "dinner", 180.0, ["gluten-free"]),
    ]

    res = await execute_concierge_query(
        question="Find us dinner under $30",
        all_venues=venues,
        travelers_dietary=frozenset(),
        travelers_min_ceiling=30.0,
        anchor_coords=LISBON_ANCHOR
    )

    # Empty candidate set produces honest hedge naming the constraint
    assert res["suggestedVenueId"] is None
    assert res["sourceEvents"] == []
    assert "No venue in the Lisbon dataset satisfies" in res["answer"]
    assert "'budget' rule eliminated" in res["answer"]


@pytest.mark.asyncio
async def test_fabricated_venue_id_rejected():
    candidates = [
        make_venue("v_real_1", "Real Venue 1", "dinner", 20.0, []),
        make_venue("v_real_2", "Real Venue 2", "dinner", 25.0, []),
    ]

    # If LLM or prompt hallucinated "v_fake_9999", the validator must override with valid candidate
    res = await execute_concierge_query(
        question="Suggest something nice for dinner",
        all_venues=candidates,
        travelers_dietary=frozenset(),
        travelers_min_ceiling=50.0,
        anchor_coords=LISBON_ANCHOR
    )

    assert res["suggestedVenueId"] in ("v_real_1", "v_real_2")
    assert res["suggestedVenueId"] != "v_fake_9999"
    assert "Real Venue" in res["answer"]

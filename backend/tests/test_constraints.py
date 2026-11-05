import pytest
from app.concierge.constraints import (
    Req, VenueCandidate, violations, rank, haversine_km, diagnose_elimination
)

# Reference anchor in Lisbon (Baixa)
LISBON_ANCHOR = (38.7139, -9.1394)


def make_venue(
    id="v_test",
    name="Test Venue",
    category="dinner",
    price=25.0,
    dietary=None,
    open_min=600,   # 10:00
    close_min=1380, # 23:00
    lat=38.7139,
    lng=-9.1394,
    rating=4.5
):
    return VenueCandidate(
        id=id,
        name=name,
        category=category,
        price_per_person=price,
        dietary_tags=dietary or [],
        open_min=open_min,
        close_min=close_min,
        lat=lat,
        lng=lng,
        rating=rating
    )


def test_budget_rule():
    req = Req(category="dinner", ceiling=30.0, dietary=frozenset(), slot_start=1140, slot_end=1260)
    
    # Boundary: price == ceiling passes
    v_pass = make_venue(price=30.0)
    assert "budget" not in violations(v_pass, req)
    
    # Boundary: price > ceiling fails
    v_fail = make_venue(price=30.01)
    assert "budget" in violations(v_fail, req)


def test_dietary_rule():
    req = Req(category="dinner", ceiling=50.0, dietary=frozenset({"vegan", "gluten-free"}), slot_start=1140, slot_end=1260)
    
    # Missing one tag fails
    v_missing = make_venue(dietary=["vegan"])
    assert "dietary" in violations(v_missing, req)
    
    # Has all tags passes
    v_ok = make_venue(dietary=["vegan", "gluten-free", "halal"])
    assert "dietary" not in violations(v_ok, req)


def test_hours_with_buffer_rule():
    # Slot: 19:00 (1140) to 21:00 (1260). Buffer: 30 min.
    # Must open <= 1110 (18:30) and close >= 1290 (21:30)
    req = Req(category="dinner", ceiling=50.0, dietary=frozenset(), slot_start=1140, slot_end=1260, buffer_min=30)
    
    # Exactly on boundary passes
    v_exact = make_venue(open_min=1110, close_min=1290)
    assert "hours" not in violations(v_exact, req)
    
    # Opens 1 min too late fails
    v_late_open = make_venue(open_min=1111, close_min=1290)
    assert "hours" in violations(v_late_open, req)
    
    # Closes 1 min too early fails
    v_early_close = make_venue(open_min=1110, close_min=1289)
    assert "hours" in violations(v_early_close, req)


def test_proximity_rule():
    # 2 km radius from Baixa
    req = Req(
        category="dinner", ceiling=50.0, dietary=frozenset(),
        slot_start=1140, slot_end=1260, anchor=LISBON_ANCHOR, radius_km=2.0
    )
    
    # Chiado (~0.35 km away) passes
    v_close = make_venue(lat=38.7108, lng=-9.1432)
    assert haversine_km(LISBON_ANCHOR, (v_close.lat, v_close.lng)) < 2.0
    assert "proximity" not in violations(v_close, req)
    
    # Belem (~6 km away) fails
    v_far = make_venue(lat=38.6976, lng=-9.2032)
    assert haversine_km(LISBON_ANCHOR, (v_far.lat, v_far.lng)) > 2.0
    assert "proximity" in violations(v_far, req)


def test_ranking_weights_40_30_30():
    req = Req(
        category="dinner", ceiling=100.0, dietary=frozenset(),
        slot_start=1140, slot_end=1260, anchor=LISBON_ANCHOR, radius_km=2.0
    )
    
    # v1: right at anchor (dist=0, prox=1.0), rating=5.0 (1.0), price=10 (head=0.9)
    # score = 0.4*1.0 + 0.3*1.0 + 0.3*0.9 = 0.97
    v1 = make_venue(id="v1", price=10.0, rating=5.0, lat=LISBON_ANCHOR[0], lng=LISBON_ANCHOR[1])
    
    # v2: 1 km away (prox=0.5), rating=4.0 (0.8), price=50 (head=0.5)
    # score = 0.4*0.5 + 0.3*0.8 + 0.3*0.5 = 0.59
    v2 = make_venue(id="v2", price=50.0, rating=4.0, lat=38.7139, lng=-9.1278)
    
    ranked = rank([v2, v1], req)
    assert ranked[0].id == "v1"
    assert ranked[1].id == "v2"


def test_20_simulated_requests_100_percent_compliant():
    """Generates 25 diverse simulated group trip requests and asserts 100% compliance."""
    venues_pool = [
        make_venue(id=f"v_{i}", category="dinner" if i % 2 == 0 else "lunch",
                   price=15.0 + (i * 5),
                   dietary=["vegetarian"] if i % 3 == 0 else (["vegan"] if i % 4 == 0 else []),
                   open_min=600, close_min=1400,
                   lat=38.7139 + (i * 0.001), lng=-9.1394 + (i * 0.001),
                   rating=3.5 + (i % 3) * 0.5)
        for i in range(30)
    ]

    for req_idx in range(25):
        cat = "dinner" if req_idx % 2 == 0 else "lunch"
        ceil = 20.0 + req_idx * 4.0
        diet = frozenset({"vegetarian"}) if req_idx % 3 == 0 else frozenset()
        slot_s = 1140 if cat == "dinner" else 750
        slot_e = 1260 if cat == "dinner" else 840

        req = Req(
            category=cat,
            ceiling=ceil,
            dietary=diet,
            slot_start=slot_s,
            slot_end=slot_e,
            anchor=LISBON_ANCHOR,
            radius_km=3.0,
            buffer_min=30
        )

        ranked = rank(venues_pool, req)

        # Assert 100% compliance on every returned venue
        for v in ranked:
            assert v.category == req.category
            assert v.price_per_person <= req.ceiling
            assert req.dietary.issubset(set(v.dietary_tags))
            assert v.open_min <= req.slot_start - req.buffer_min
            assert v.close_min >= req.slot_end + req.buffer_min
            assert haversine_km(req.anchor, (v.lat, v.lng)) <= req.radius_km
            assert violations(v, req) == []


def test_diagnose_elimination():
    req = Req(category="dinner", ceiling=15.0, dietary=frozenset({"halal"}), slot_start=1140, slot_end=1260)
    v1 = make_venue(price=50.0, dietary=[]) # violates budget & dietary
    v2 = make_venue(price=60.0, dietary=[]) # violates budget & dietary
    
    diag = diagnose_elimination([v1, v2], req)
    assert diag["budget"] == 2
    assert diag["dietary"] == 2

from dataclasses import dataclass
from math import radians, sin, cos, sqrt, asin
from typing import List, Tuple, Optional, Dict, Set


@dataclass(frozen=True)
class Req:
    category: str
    ceiling: float
    dietary: frozenset
    slot_start: int          # minutes since midnight (e.g. 19:00 = 1140)
    slot_end: int            # minutes since midnight (e.g. 21:00 = 1260)
    anchor: Optional[Tuple[float, float]] = None  # (lat, lng)
    radius_km: float = 2.0
    buffer_min: int = 30


@dataclass
class VenueCandidate:
    id: str
    name: str
    category: str
    price_per_person: float
    dietary_tags: List[str]
    open_min: int
    close_min: int
    lat: float
    lng: float
    rating: float
    description: str = ""


def haversine_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    R = 6371.0088
    p1, p2 = radians(a[0]), radians(b[0])
    h = sin((p2 - p1) / 2) ** 2 + cos(p1) * cos(p2) * sin(radians(b[1] - a[1]) / 2) ** 2
    return 2 * R * asin(sqrt(h))


def violations(v: VenueCandidate, r: Req) -> List[str]:
    out = []
    # Budget check (ceiling is inclusive)
    if v.price_per_person > r.ceiling:
        out.append("budget")
    
    # Dietary check: all required tags must be supported by the venue
    if not r.dietary.issubset(set(v.dietary_tags)):
        out.append("dietary")
        
    # Hours check with required buffer before opening and after closing
    if not (v.open_min <= (r.slot_start - r.buffer_min) and v.close_min >= (r.slot_end + r.buffer_min)):
        out.append("hours")
        
    # Proximity check relative to anchor point
    if r.anchor is not None:
        dist = haversine_km(r.anchor, (v.lat, v.lng))
        if dist > r.radius_km:
            out.append("proximity")
            
    return out


def rank(venues: List[VenueCandidate], r: Req) -> List[VenueCandidate]:
    # Category match and zero violations
    ok = [v for v in venues if r.category.lower() == v.category.lower() and not violations(v, r)]
    
    def score(v: VenueCandidate) -> float:
        if r.anchor:
            d = haversine_km(r.anchor, (v.lat, v.lng))
            prox = max(0.0, 1.0 - (d / r.radius_km))
        else:
            prox = 1.0
            
        rating_score = min(1.0, max(0.0, v.rating / 5.0))
        
        # Budget headroom (relative savings against ceiling)
        if r.ceiling > 0:
            head = max(0.0, (r.ceiling - v.price_per_person) / r.ceiling)
        else:
            head = 0.0
            
        return (0.4 * prox) + (0.3 * rating_score) + (0.3 * head)

    return sorted(ok, key=score, reverse=True)


def diagnose_elimination(venues: List[VenueCandidate], r: Req) -> Dict[str, int]:
    """Diagnoses which constraint eliminated the most venues of the target category."""
    counts = {"budget": 0, "dietary": 0, "hours": 0, "proximity": 0, "category_mismatch": 0}
    cat_venues = [v for v in venues if v.category.lower() == r.category.lower()]
    if not cat_venues:
        counts["category_mismatch"] = len(venues)
        return counts

    for v in cat_venues:
        v_issues = violations(v, r)
        for issue in v_issues:
            counts[issue] += 1
    return counts

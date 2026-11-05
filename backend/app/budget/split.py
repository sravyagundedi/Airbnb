from typing import List, Dict, Any


def even_split(total_cents: int, n: int) -> List[int]:
    """
    Distributes total_cents among n participants using largest remainder.
    Guarantees that sum(shares) == total_cents.
    """
    if n <= 0:
        raise ValueError("Participant count n must be at least 1")
    if total_cents < 0:
        raise ValueError("total_cents cannot be negative")
    base, rem = divmod(total_cents, n)
    return [base + (1 if i < rem else 0) for i in range(n)]


def weighted_split(total_cents: int, weights: List[float]) -> List[int]:
    """
    Distributes total_cents according to weights using the largest-remainder method (Hamilton-Hare).
    Guarantees that sum(shares) == total_cents exactly, with zero floating point drift.
    """
    if not weights:
        raise ValueError("Weights list cannot be empty")
    if total_cents < 0:
        raise ValueError("total_cents cannot be negative")
    
    s = sum(weights)
    if s <= 0:
        # Fall back to even split if all weights are zero
        return even_split(total_cents, len(weights))

    raw = [total_cents * w for w in weights]
    shares = [int(r // s) for r in raw]
    left = total_cents - sum(shares)
    
    # Sort indices by remainder descending
    order = sorted(range(len(weights)), key=lambda i: raw[i] % s, reverse=True)
    for i in order[:left]:
        shares[i] += 1

    assert sum(shares) == total_cents, f"Split error: {sum(shares)} != {total_cents}"
    return shares


def calculate_running_totals(items_with_cost: List[Dict[str, Any]], participants: List[int]) -> Dict[int, int]:
    """
    Calculates per-person running total in integer cents for a list of items.
    Each item has 'cost_cents' and optionally 'attendees' (default to all participants).
    Returns mapping: {user_id: total_cents}
    """
    totals = {uid: 0 for uid in participants}
    if not participants:
        return totals

    for item in items_with_cost:
        cost_cents = int(item.get("cost_cents", 0))
        attendees = item.get("attendees") or participants
        active_attendees = [uid for uid in attendees if uid in totals]
        if not active_attendees:
            continue
        
        shares = even_split(cost_cents, len(active_attendees))
        for uid, share in zip(active_attendees, shares):
            totals[uid] += share

    return totals

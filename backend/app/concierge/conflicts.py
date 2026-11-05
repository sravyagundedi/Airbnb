from collections import defaultdict
from typing import List, Dict, Any, Tuple


def detect_conflicts(
    items: List[Any],
    per_person_totals: Dict[int, int],
    ceilings: Dict[int, int]
) -> List[Dict[str, Any]]:
    """
    Detects scheduling overlaps and budget breaches.
    Uses running-max-end scan to correctly catch overlaps with long duration items.
    Returns list of conflict descriptors.
    """
    conflicts = []

    # 1. Schedule Overlaps (per day)
    by_day = defaultdict(list)
    for it in items:
        # Support both BoardItem objects and dicts
        day = getattr(it, "day_index", None) or it.get("dayIndex") or it.get("day_index")
        by_day[day].append(it)

    for day, day_items in by_day.items():
        # Sort items primarily by start time, secondary by end time
        def get_times(x):
            start = getattr(x, "start_min", None)
            if start is None:
                start = x.get("startMin", 0)
            end = getattr(x, "end_min", None)
            if end is None:
                end = x.get("endMin", 0)
            return (start, end)

        sorted_items = sorted(day_items, key=get_times)

        # Running max end tracker
        running_max_end = -1
        running_max_item_id = None

        for item in sorted_items:
            s, e = get_times(item)
            item_id = getattr(item, "id", None) or item.get("id")

            if running_max_end > s:
                # Overlap detected!
                conflicts.append({
                    "type": "overlap",
                    "dayIndex": day,
                    "itemIds": [running_max_item_id, item_id],
                    "message": f"Time overlap detected on Day {day} between items {running_max_item_id} and {item_id}"
                })

            if e > running_max_end:
                running_max_end = e
                running_max_item_id = item_id

    # 2. Budget Breaches
    for uid, total_cents in per_person_totals.items():
        ceiling_cents = ceilings.get(uid)
        if ceiling_cents is not None and total_cents > ceiling_cents:
            conflicts.append({
                "type": "budgetBreach",
                "userId": uid,
                "totalCents": total_cents,
                "ceilingCents": ceiling_cents,
                "message": f"User {uid} exceeded budget ceiling: {total_cents / 100:.2f} > {ceiling_cents / 100:.2f}"
            })

    return conflicts

import asyncio
from typing import Dict, Any, Tuple, Optional, List


def time_to_min(time_str: str) -> int:
    parts = time_str.split(":")
    return int(parts[0]) * 60 + int(parts[1])


class BoardItem:
    def __init__(
        self,
        id: int,
        trip_id: int,
        venue_id: str,
        venue_name: str,
        category: str,
        day_index: int,
        start_time: str,
        end_time: str,
        lifecycle_stage: str = "drafting",
        pinned_by_user_id: int = 0,
        position_version: int = 1,
        price_per_person: float = 0.0,
        dietary_tags: Optional[List[str]] = None,
        lat: float = 38.7139,
        lng: float = -9.1394,
    ):
        self.id = id
        self.trip_id = trip_id
        self.venue_id = venue_id
        self.venue_name = venue_name
        self.category = category
        self.day_index = day_index
        self.start_time = start_time
        self.end_time = end_time
        self.start_min = time_to_min(start_time)
        self.end_min = time_to_min(end_time)
        self.lifecycle_stage = lifecycle_stage
        self.pinned_by_user_id = pinned_by_user_id
        self.position_version = position_version
        self.price_per_person = price_per_person
        self.dietary_tags = dietary_tags or []
        self.lat = lat
        self.lng = lng
        self.dirty = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tripId": self.trip_id,
            "venueId": self.venue_id,
            "venueName": self.venue_name,
            "category": self.category,
            "dayIndex": self.day_index,
            "startTime": self.start_time,
            "endTime": self.end_time,
            "startMin": self.start_min,
            "endMin": self.end_min,
            "lifecycleStage": self.lifecycle_stage,
            "pinnedByUserId": self.pinned_by_user_id,
            "positionVersion": self.position_version,
            "pricePerPerson": self.price_per_person,
            "dietaryTags": self.dietary_tags,
            "lat": self.lat,
            "lng": self.lng,
        }


# Strict lifecycle transitions table
ALLOWED_TRANSITIONS = {
    ("drafting", "voting"): ["planner", "leader", "admin"],
    ("voting", "locked"): ["planner", "leader", "admin"],
    ("drafting", "locked"): ["leader", "admin"],
    ("locked", "drafting"): ["leader", "admin"],  # Leader override only
}


class Board:
    def __init__(self, trip_id: int, items: Optional[List[BoardItem]] = None):
        self.trip_id = trip_id
        self.items: Dict[int, BoardItem] = {i.id: i for i in (items or [])}
        self._lock: Optional[asyncio.Lock] = None
        self._loop = None

    @property
    def lock(self) -> asyncio.Lock:
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if self._lock is None or self._loop != current_loop:
            self._lock = asyncio.Lock()
            self._loop = current_loop
        return self._lock

    async def pin(self, item: BoardItem, actor_role: str) -> Tuple[str, Optional[str], Optional[BoardItem]]:
        async with self.lock:
            if actor_role == "viewer":
                return ("rejected", "insufficient_role", None)
            item.dirty = True
            self.items[item.id] = item
            return ("ok", None, item)

    async def move(
        self,
        item_id: int,
        seen_version: int,
        day: int,
        start_time: str,
        end_time: str,
        actor_role: str
    ) -> Tuple[str, Optional[str], Optional[BoardItem]]:
        async with self.lock:
            if actor_role == "viewer":
                return ("rejected", "insufficient_role", None)
            if item_id not in self.items:
                return ("rejected", "not_found", None)
            
            it = self.items[item_id]

            if it.lifecycle_stage == "locked" and actor_role not in ("leader", "admin"):
                return ("rejected", "locked", it)
            if it.lifecycle_stage == "voting":
                return ("rejected", "voting", it)

            # Optimistic concurrency version check
            if seen_version != it.position_version:
                return ("conflict", "version_mismatch", it)  # Loser gets current server state

            it.day_index = day
            it.start_time = start_time
            it.end_time = end_time
            it.start_min = time_to_min(start_time)
            it.end_min = time_to_min(end_time)
            it.position_version += 1
            it.dirty = True
            return ("ok", None, it)

    async def transition(
        self,
        item_id: int,
        target_stage: str,
        actor_role: str
    ) -> Tuple[str, Optional[str], Optional[BoardItem]]:
        async with self.lock:
            if item_id not in self.items:
                return ("rejected", "not_found", None)
            it = self.items[item_id]
            current = it.lifecycle_stage
            
            transition_key = (current, target_stage)
            if transition_key not in ALLOWED_TRANSITIONS:
                return ("rejected", f"illegal_transition_{current}_to_{target_stage}", it)

            allowed_roles = ALLOWED_TRANSITIONS[transition_key]
            if actor_role not in allowed_roles:
                return ("rejected", "insufficient_role", it)

            it.lifecycle_stage = target_stage
            it.position_version += 1
            it.dirty = True
            return ("ok", None, it)

    async def remove(self, item_id: int, actor_role: str) -> Tuple[str, Optional[str], Optional[BoardItem]]:
        async with self.lock:
            if actor_role == "viewer":
                return ("rejected", "insufficient_role", None)
            if item_id not in self.items:
                return ("rejected", "not_found", None)
            it = self.items[item_id]
            if it.lifecycle_stage == "locked" and actor_role not in ("leader", "admin"):
                return ("rejected", "locked", it)
            del self.items[item_id]
            return ("ok", None, it)

    async def get_snapshot(self) -> List[Dict[str, Any]]:
        async with self.lock:
            return [it.to_dict() for it in self.items.values()]

    async def get_dirty_items(self) -> List[BoardItem]:
        async with self.lock:
            dirty = [it for it in self.items.values() if it.dirty]
            for it in dirty:
                it.dirty = False
            return dirty

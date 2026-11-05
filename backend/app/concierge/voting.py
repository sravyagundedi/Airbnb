import asyncio
import time
from typing import Dict, List, Any, Optional, Callable, Awaitable


class VoteSession:
    def __init__(
        self,
        vote_id: str,
        trip_id: int,
        item_ids: List[int],
        duration_seconds: int = 30,
        opened_by_user_id: int = 0,
        on_resolve: Optional[Callable[["VoteSession"], Awaitable[None]]] = None,
    ):
        self.vote_id = vote_id
        self.trip_id = trip_id
        self.item_ids = item_ids
        self.opened_by_user_id = opened_by_user_id
        self.opened_at = time.time()
        self.duration_seconds = duration_seconds
        self.closes_at = self.opened_at + duration_seconds
        self.votes: Dict[int, int] = {}  # user_id -> chosen item_id (one vote per user, re-vote replaces)
        self.resolved = False
        self.winner_item_id: Optional[int] = None
        self.on_resolve = on_resolve
        self.timer_task: Optional[asyncio.Task] = None

    def start_timer(self):
        self.timer_task = asyncio.create_task(self._auto_close_timer())

    async def _auto_close_timer(self):
        try:
            now = time.time()
            remaining = max(0.0, self.closes_at - now)
            await asyncio.sleep(remaining)
            if not self.resolved and self.on_resolve:
                await self.on_resolve(self)
        except asyncio.CancelledError:
            pass  # Early resolution cancelled the timer

    def cast_vote(self, user_id: int, item_id: int, actor_role: str, total_eligible_voters: int = 0) -> bool:
        if self.resolved:
            return False
        if actor_role == "viewer":
            return False
        if item_id not in self.item_ids:
            return False

        # One vote per user; re-vote replaces earlier choice
        self.votes[user_id] = item_id

        # Check early close condition: all eligible planners/leaders have voted
        if total_eligible_voters > 0 and len(self.votes) >= total_eligible_voters:
            if self.timer_task and not self.timer_task.done():
                self.timer_task.cancel()
            return True  # Signal caller that everyone voted and can resolve immediately
        return False

    def tally(self, item_pinned_timestamps: Dict[int, float], leader_choice: Optional[int] = None) -> int:
        """
        Tallies votes.
        Tie break rules:
        1. Earliest pinned
        2. Leader choice override
        """
        counts = {iid: 0 for iid in self.item_ids}
        for chosen in self.votes.values():
            if chosen in counts:
                counts[chosen] += 1

        max_count = -1
        winners = []
        for iid, cnt in counts.items():
            if cnt > max_count:
                max_count = cnt
                winners = [iid]
            elif cnt == max_count:
                winners.append(iid)

        if len(winners) == 1:
            self.winner_item_id = winners[0]
        else:
            # Tie breaker: earliest pinned
            def sort_key(iid):
                # Earliest pinned timestamp first
                pinned_ts = item_pinned_timestamps.get(iid, float("inf"))
                # If leader picked this one, give secondary preference
                leader_pref = 0 if (leader_choice is not None and iid == leader_choice) else 1
                return (pinned_ts, leader_pref)

            sorted_ties = sorted(winners, key=sort_key)
            self.winner_item_id = sorted_ties[0]

        self.resolved = True
        return self.winner_item_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "voteId": self.vote_id,
            "tripId": self.trip_id,
            "itemIds": self.item_ids,
            "openedBy": self.opened_by_user_id,
            "openedAt": int(self.opened_at * 1000),
            "closesAt": int(self.closes_at * 1000),
            "remainingSeconds": max(0, int(self.closes_at - time.time())),
            "votes": self.votes,
            "resolved": self.resolved,
            "winnerItemId": self.winner_item_id,
        }

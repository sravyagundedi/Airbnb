import asyncio
import time
import json
from typing import Dict, Any, Optional, Set
from fastapi import WebSocket
from app.realtime.board import Board, BoardItem
from app.concierge.voting import VoteSession
from app.logging_conf import JSONFormatter
import logging

logger = logging.getLogger("warroom.realtime")


class ConnectionManager:
    def __init__(self):
        # trip_id -> {user_id: WebSocket}
        self.rooms: Dict[int, Dict[int, WebSocket]] = {}
        # trip_id -> Board
        self.boards: Dict[int, Board] = {}
        # trip_id -> VoteSession
        self.active_votes: Dict[int, VoteSession] = {}
        # trip_id -> leader_user_id
        self.trip_leaders: Dict[int, int] = {}
        # (trip_id, user_id) -> pending leave Task (10s reconnect grace)
        self.pending_leaves: Dict[tuple, asyncio.Task] = {}
        # trip_id -> leader disconnect timer Task (15s grace)
        self.leader_disconnect_tasks: Dict[int, asyncio.Task] = {}
        # trip_id -> bool indicating if room actions are frozen due to leader disconnect
        self.frozen_rooms: Dict[int, bool] = {}
        # Background task handle for batched persistence
        self.persistence_task: Optional[asyncio.Task] = None

    def get_or_create_board(self, trip_id: int, initial_items: Optional[list] = None) -> Board:
        if trip_id not in self.boards:
            self.boards[trip_id] = Board(trip_id, initial_items or [])
        return self.boards[trip_id]

    async def broadcast(self, trip_id: int, event: str, payload: Any, exclude_user_id: Optional[int] = None):
        user_sockets = self.rooms.get(trip_id, {})
        if not user_sockets:
            return

        message = {
            "event": event,
            "tripId": trip_id,
            "payload": payload,
            "ts": int(time.time() * 1000)
        }

        tasks = []
        for uid, ws in list(user_sockets.items()):
            if exclude_user_id is not None and uid == exclude_user_id:
                continue
            tasks.append(self._safe_send(ws, message, uid, trip_id))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_send(self, ws: WebSocket, msg: dict, user_id: int, trip_id: int):
        try:
            await ws.send_json(msg)
        except Exception as e:
            logger.warning(f"Failed to send to user {user_id} in trip {trip_id}: {e}")

    async def send_to_user(self, trip_id: int, user_id: int, event: str, payload: Any):
        ws = self.rooms.get(trip_id, {}).get(user_id)
        if ws:
            msg = {
                "event": event,
                "tripId": trip_id,
                "payload": payload,
                "ts": int(time.time() * 1000)
            }
            await self._safe_send(ws, msg, user_id, trip_id)

    def cancel_pending_leave(self, trip_id: int, user_id: int) -> bool:
        """Returns True if a pending leave was cancelled (i.e. user reconnected within grace)."""
        key = (trip_id, user_id)
        task = self.pending_leaves.pop(key, None)
        if task and not task.done():
            task.cancel()
            return True
        return False

    def on_leader_reconnected(self, trip_id: int):
        task = self.leader_disconnect_tasks.pop(trip_id, None)
        if task and not task.done():
            task.cancel()
        if self.frozen_rooms.get(trip_id, False):
            self.frozen_rooms[trip_id] = False
            asyncio.create_task(self.broadcast(
                trip_id,
                "trip.leader.resumed",
                {"message": "Trip leader returned. Board controls unfrozen."}
            ))

    def schedule_leader_disconnect_rule(self, trip_id: int):
        async def _grace():
            try:
                await asyncio.sleep(15)  # 15s grace rule
                self.frozen_rooms[trip_id] = True
                await self.broadcast(
                    trip_id,
                    "trip.leader.disconnected",
                    {
                        "message": "Trip leader disconnected. Board lock/finalize and vote actions frozen until leader returns.",
                        "frozen": True
                    }
                )
            except asyncio.CancelledError:
                pass

        self.leader_disconnect_tasks[trip_id] = asyncio.create_task(_grace())

    def get_active_participant_count(self, trip_id: int) -> int:
        return len(self.rooms.get(trip_id, {}))


manager = ConnectionManager()

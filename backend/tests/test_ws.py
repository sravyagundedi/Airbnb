import pytest
import time
from starlette.testclient import TestClient
from app.main import app
from app.realtime.manager import manager


def test_ws_authentication_and_snapshot(seed_users_and_trip):
    tokens = seed_users_and_trip
    client = TestClient(app)

    # 1. Invalid token rejected with code 4401
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/trips/1?token=bad-token"):
            pass

    # 2. Valid planner connects and receives immediate snapshot
    t0 = time.perf_counter()
    with client.websocket_connect(f"/ws/trips/1?token={tokens['planner_token']}") as ws:
        msg = ws.receive_json()
        elapsed_s = time.perf_counter() - t0
        
        # Verify snapshot arrived in under 2 seconds
        assert elapsed_s < 2.0
        assert msg["event"] == "trip.room.snapshot"
        assert msg["payload"]["tripId"] == 1
        assert "items" in msg["payload"]
        assert "budgetTotals" in msg["payload"]

        # Test sync ping / pong
        ws.send_json({"event": "trip.sync.ping", "payload": {"clientSentAt": 123456}})
        
        # Read until trip.sync.pong arrives (presence update may precede pong)
        pong = None
        for _ in range(5):
            incoming = ws.receive_json()
            if incoming.get("event") == "trip.sync.pong":
                pong = incoming
                break
        
        assert pong is not None
        assert pong["event"] == "trip.sync.pong"
        assert pong["payload"]["clientSentAt"] == 123456
        assert "serverReceivedAt" in pong["payload"]


def test_ws_two_clients_presence(seed_users_and_trip):
    tokens = seed_users_and_trip
    client = TestClient(app)

    with client.websocket_connect(f"/ws/trips/1?token={tokens['leader_token']}") as ws1:
        snap1 = ws1.receive_json()
        assert snap1["event"] == "trip.room.snapshot"

        # Read ws1's own join presence update
        own_presence = ws1.receive_json()
        assert own_presence["event"] == "trip.presence.update"
        assert own_presence["payload"]["action"] == "joined"

        # Second client joins
        with client.websocket_connect(f"/ws/trips/1?token={tokens['planner_token']}") as ws2:
            snap2 = ws2.receive_json()
            assert snap2["event"] == "trip.room.snapshot"

            # ws1 should receive presence update for ws2
            presence = ws1.receive_json()
            assert presence["event"] == "trip.presence.update"
            assert presence["payload"]["action"] == "joined"
            assert presence["payload"]["participantId"] == 3
            assert presence["payload"]["participantCount"] >= 2

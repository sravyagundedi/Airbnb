import asyncio
import json
import time
import statistics
import websockets
import httpx
import os
import sys

# Base URLs
HTTP_BASE = os.getenv("API_URL", "http://127.0.0.1:8000")
WS_BASE = os.getenv("WS_URL", "ws://127.0.0.1:8000")


async def setup_test_room(client: httpx.AsyncClient):
    # 1. Register leader
    t_id = int(time.time() * 1000) % 100000
    leader_reg = await client.post(f"{HTTP_BASE}/api/v1/auth/register", json={
        "email": f"leader_{t_id}@loadtest.local",
        "password": "Password123!",
        "display_name": "Load Leader",
        "role": "leader"
    })
    leader_token = leader_reg.json()["access_token"]

    # 2. Create trip
    trip_res = await client.post(
        f"{HTTP_BASE}/api/v1/trips",
        headers={"Authorization": f"Bearer {leader_token}"},
        json={"title": "Load Test Room", "destination": "Lisbon", "max_participants": 20}
    )
    trip_data = trip_res.json()
    trip_id = trip_data["id"]
    invite_code = trip_data["invite_code"]

    # 3. Register participants and join
    tokens = [leader_token]
    for i in range(1, 10):
        reg = await client.post(f"{HTTP_BASE}/api/v1/auth/register", json={
            "email": f"client_{t_id}_{i}@loadtest.local",
            "password": "Password123!",
            "display_name": f"Planner {i}",
            "role": "planner"
        })
        tok = reg.json()["access_token"]
        await client.post(
            f"{HTTP_BASE}/api/v1/trips/join",
            headers={"Authorization": f"Bearer {tok}"},
            json={"inviteCode": invite_code}
        )
        tokens.append(tok)

    return trip_id, tokens


async def run_load_test():
    print("=" * 60)
    print("WAR ROOM LOAD & LATENCY BENCHMARK")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=10.0) as http_client:
        # Check health
        try:
            h = await http_client.get(f"{HTTP_BASE}/health")
            if h.status_code != 200:
                print("Server not running at", HTTP_BASE)
                return
        except Exception as e:
            print(f"Cannot connect to server at {HTTP_BASE}: {e}")
            return

        print("Setting up test room and 10 authenticated participants...")
        trip_id, tokens = await setup_test_room(http_client)
        print(f"Room ready: Trip ID {trip_id} with {len(tokens)} members.")

        # Latency trackers
        ping_latencies_ms = []
        fanout_latencies_ms = []
        conflicts_count = 0
        total_moves = 0

        async def client_worker(client_idx: int, token: str):
            nonlocal conflicts_count, total_moves
            ws_url = f"{WS_BASE}/ws/trips/{trip_id}?token={token}"
            async with websockets.connect(ws_url) as ws:
                # Read snapshot
                snap = json.loads(await ws.recv())

                # Loop for 15 iterations
                for cycle in range(15):
                    # 1. Sync Ping
                    t0 = time.perf_counter()
                    await ws.send(json.dumps({
                        "event": "trip.sync.ping",
                        "payload": {"clientSentAt": t0}
                    }))

                    # Read messages until pong
                    while True:
                        msg = json.loads(await ws.recv())
                        if msg["event"] == "trip.sync.pong":
                            t_rtt = (time.perf_counter() - t0) * 1000
                            ping_latencies_ms.append(t_rtt)
                            break
                        elif msg["event"] == "trip.board.conflict":
                            conflicts_count += 1

                    # 2. Concurrent Move on shared item if client 0 or client 1
                    if client_idx in (0, 1):
                        total_moves += 1
                        await ws.send(json.dumps({
                            "event": "trip.board.move",
                            "payload": {
                                "itemId": 1,
                                "seenVersion": 1,
                                "dayIndex": 1,
                                "startTime": f"1{client_idx}:00",
                                "endTime": f"1{client_idx}:45"
                            }
                        }))

                    await asyncio.sleep(0.5)

        print("Launching 10 concurrent WebSocket clients...")
        t_start = time.perf_counter()
        tasks = [client_worker(i, tok) for i, tok in enumerate(tokens)]
        await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.perf_counter() - t_start

        # REST benchmarks
        print("\nBenchmarking non-AI REST latency (50 samples)...")
        rest_latencies_ms = []
        for _ in range(50):
            t0 = time.perf_counter()
            r = await http_client.get(f"{HTTP_BASE}/api/v1/destinations/Lisbon/venues?radiusKm=5.0")
            rest_latencies_ms.append((time.perf_counter() - t0) * 1000)

        # AI endpoint benchmarks
        print("Benchmarking AI Concierge latency (10 queries)...")
        ai_latencies_ms = []
        for q_idx in range(10):
            t0 = time.perf_counter()
            r = await http_client.post(
                f"{HTTP_BASE}/api/v1/trips/{trip_id}/ai/ask",
                headers={"Authorization": f"Bearer {tokens[0]}"},
                json={"question": "Where can we have a good vegetarian lunch under 25 euros?"}
            )
            ai_latencies_ms.append((time.perf_counter() - t0) * 1000)

        # Metrics calculation
        def p50(arr): return statistics.median(arr) if arr else 0.0
        def p95(arr):
            if not arr: return 0.0
            sorted_arr = sorted(arr)
            idx = int(0.95 * len(sorted_arr))
            return sorted_arr[min(idx, len(sorted_arr) - 1)]

        print("\n" + "=" * 60)
        print("PERFORMANCE BENCHMARK RESULTS")
        print("=" * 60)
        print(f"Total Test Run Time: {total_duration:.2f} s")
        print(f"WebSocket Clients Connected: {len(tokens)}")
        print(f"Total Sync Ping Samples: {len(ping_latencies_ms)}")
        print(f"Sync Ping RTT p50: {p50(ping_latencies_ms):.2f} ms (Target < 100 ms)")
        print(f"Sync Ping RTT p95: {p95(ping_latencies_ms):.2f} ms (Target < 100 ms)")
        print(f"Concurrent Item Moves: {total_moves} | Conflicts Handled: {conflicts_count}")
        print(f"REST Non-AI p50: {p50(rest_latencies_ms):.2f} ms | p95: {p95(rest_latencies_ms):.2f} ms")
        print(f"AI Concierge p50: {p50(ai_latencies_ms):.2f} ms | p95: {p95(ai_latencies_ms):.2f} ms")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_load_test())

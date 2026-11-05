# WarRoom API & Real-Time Protocol Specification

## 1. Authentication & Security Endpoints

### `POST /api/v1/auth/register`
Creates a new traveler account with role, budget ceiling, and dietary requirements.
- **Request Body**:
```json
{
  "email": "planner@example.com",
  "password": "Password123!",
  "display_name": "Maria Silva",
  "role": "planner",
  "budget_ceiling": 150,
  "dietary_tags": ["vegetarian", "gluten-free"]
}
```
- **Response** (`201 Created`):
```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### `POST /api/v1/auth/login`
Authenticates with email and password, returning access token (30 min) and refresh token (7 days).

### `POST /api/v1/auth/refresh`
Issues a fresh access and refresh token pair given a valid refresh token.

### `GET /api/v1/auth/me`
Returns current authenticated user profile. Requires `Authorization: Bearer <token>`.

---

## 2. Trip Rooms Endpoints

### `POST /api/v1/trips`
Creates a new trip room. The creator is assigned role `leader` in `trip_members`.
- **Response** (`201 Created`):
```json
{
  "id": 1,
  "title": "Lisbon Summer Retreat",
  "destination": "Lisbon",
  "invite_code": "AB-K9X2",
  "max_participants": 10,
  "creator_id": 2,
  "created_at": "2026-06-01T10:00:00Z",
  "members_count": 1
}
```

### `POST /api/v1/trips/join`
Joins a trip room using an invite code. Enforces `max_participants`.
- **Request Body**: `{"inviteCode": "AB-K9X2"}`

### `GET /api/v1/trips/{trip_id}/analytics`
Derives session analytics strictly from the append-only `events` log table.
- **Response**:
```json
{
  "tripId": 1,
  "planningDurationMinutes": 24.5,
  "peakConcurrentPlanners": 4,
  "aiQuestionsCount": 6,
  "conflictsFlagged": 3,
  "conflictsResolved": 3,
  "perPersonBreakdown": {
    "2": 45.50,
    "3": 45.50
  }
}
```

---

## 3. Lisbon Venues & Catalog Endpoints

### `GET /api/v1/destinations/{destination}/venues`
Filters Lisbon venues with SQL bounding-box prefilter and Python Haversine calculation.
- **Query Params**:
  - `near`: `lat,lng` (e.g. `38.7139,-9.1394`)
  - `radiusKm`: float (e.g. `2.0`)
  - `category`: string (`dinner`, `lunch`, `breakfast`, `activity`, `nightlife`, `transit`, `lodging`)

### `GET /api/v1/recommendations`
Serves hybrid recommendations for user or group based on collaborative item-item cosine similarity and user feature centroids.

---

## 4. AI Concierge Endpoints

### `POST /api/v1/trips/{trip_id}/ai/ask`
Executes RAG-grounded Concierge query. Enforces deterministic hard constraints, takes top 5 candidates, calls LLM with 2.5s timeout, validates citations in code, and substitutes verified DB prices.
- **Request Body**:
```json
{
  "question": "Where can we have a vegetarian dinner under 25 euros near Chiado?",
  "anchor_venue_id": "v_3391"
}
```
- **Response**:
```json
{
  "answer": "Based on your requirements, I recommend Taberna da Rua das Flores (dinner). It costs approximately €22.00 per person and holds a 4.4★ rating.",
  "suggestedVenueId": "v_3391",
  "sourceEvents": ["venue_v_3391"],
  "generatedAt": "2026-06-01T12:00:00Z",
  "latencyMs": 42.5
}
```

---

## 5. WebSocket Protocol (`/ws/trips/{trip_id}?token={jwt}`)

### Handshake
1. Validates JWT token from query string. If invalid, closes with code `4401`.
2. Checks room membership. If not a member, closes with code `4403`.
3. Sends authoritative room snapshot immediately:
```json
{
  "event": "trip.room.snapshot",
  "tripId": 1,
  "payload": {
    "items": [...],
    "messages": [...],
    "members": [...],
    "activeParticipants": [2, 3],
    "budgetTotals": {"2": 2200, "3": 2200},
    "conflicts": [],
    "activeVote": null,
    "frozen": false
  }
}
```

### Upstream Messages (Client -> Server)
| Event | Payload | Description |
|---|---|---|
| `trip.sync.ping` | `{"clientSentAt": 1718000000000}` | Latency & clock drift probe |
| `trip.board.pin` | `{"venueId": "v_3391", "dayIndex": 1, "startTime": "19:00", "endTime": "21:00"}` | Pin venue to day |
| `trip.board.move` | `{"itemId": 1, "seenVersion": 1, "dayIndex": 2, "startTime": "12:00", "endTime": "13:30"}` | Optimistic move with version check |
| `trip.board.lock` | `{"itemId": 1}` | Lock item (Leader only) |
| `trip.board.unlock` | `{"itemId": 1}` | Unlock item (Leader only) |
| `trip.board.remove` | `{"itemId": 1}` | Remove item |
| `trip.chat.message` | `{"content": "Shall we book this?"}` | Sanitized chat message |
| `trip.chat.typing` | `{}` | Broadcast typing indicator |
| `trip.chat.reaction` | `{"messageId": 12, "emoji": "👍"}` | Emoji reaction |
| `trip.vote.open` | `{"itemIds": [1, 2], "durationSeconds": 30}` | Open contested slot vote |
| `trip.vote.cast` | `{"itemId": 1}` | Cast vote choice |

### Downstream Events (Server -> Client)
| Event | Description |
|---|---|
| `trip.sync.pong` | Returns `clientSentAt` and `serverReceivedAt` |
| `trip.board.update` | Fan-out of pinned, moved, locked, or removed items with recomputed budget totals |
| `trip.board.conflict` | Targeted to loser on version mismatch with latest authoritative server state |
| `trip.presence.update` | Participant joined/left with active count |
| `trip.leader.disconnected` | 15s grace expiry: board locks and voting frozen |
| `trip.leader.resumed` | Leader returned: controls unfrozen |
| `trip.vote.opened` | Contested vote opened with countdown timer |
| `trip.vote.cast` | Vote counter update |
| `trip.vote.resolved` | Winner item locked and losers removed simultaneously |

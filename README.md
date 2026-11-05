# AI Trip War Room

> **Collaborative Group Itinerary Canvas & Real-Time Logistics Engine**  
> *Derived from the Airbnb Intern PRD.*

---

## 1. Project Overview

AI Trip War Room is an end-to-end, real-time group travel planning platform built with a high-performance **FastAPI** backend, native **WebSockets**, an authoritative in-memory state machine, a deterministic **RAG AI Concierge**, an integer-cent **Hamilton-Hare budget engine**, and a modern **React (Vite)** canvas.

### Core Features
- **Worldwide Multi-Country & Dynamic Currency**: Real-time group planning for **any place in the world**. Select from 20+ countries or custom destinations with automatic local currency resolution (JPY ¥, EUR €, USD $, GBP £, INR ₹, AED, AUD A$, etc.) and dynamic generation of authentic nearby places.
- **Authoritative In-Memory Board**: Room-level mutex concurrency with optimistic versioning (`position_version`). Instant conflict rollback toasts on concurrent edits.
- **Strict Role-Based Access Control (RBAC)**: 4 distinct roles (`Viewer`, `Planner`, `Leader`, `Admin`) enforced across REST and WebSocket paths.
- **RAG-Grounded AI Concierge**: Hard constraint filtering (budget, dietary union, hours with 30-min buffer, 2 km radius) + 40/30/30 ranking formula. Code-side citation validation with honest hedges and local currency adaptation.
- **Hamilton-Hare Integer-Cent Budget Engine**: Zero floating-point drift. Guarantees that shares sum exactly to total cents 100% of the time across all global currencies.
- **Contested Slot Voting**: Automatic overlap conflict detection with timed voting countdowns and deterministic tie-breaking.
- **Offline-Evaluated Hybrid Recommender**: Collaborative item-item cosine similarity + user feature centroids achieving **Precision@5 $\ge$ 0.70**.
- **Append-Only Event Reconciliation**: All analytics derive strictly from the `events` table.

---

## 2. Quick Start Guide

### Prerequisites
- Python 3.11+
- Node.js 18+ & npm
- Docker & Docker Compose (optional for PostgreSQL)

### Step 1: Environment Setup
```bash
# Clone the repository
git clone <repo-url>
cd Airbnb

# Copy environment template (zero-tolerance secrets rule enforced)
cp .env.example .env
```

### Step 2: Backend Setup
```bash
# Create and activate Python virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install backend dependencies
pip install -r backend/requirements.txt

# Seed the authentic Lisbon dataset into the database
python backend/scripts/seed_venues.py

# Generate synthetic interactions & train hybrid recommender
python backend/app/reco/train.py
```

### Step 3: Run Automated Tests
```bash
# Run full Pytest suite (28 tests covering global destinations, board, budget, constraints, RBAC, WS, and AI)
pytest backend/tests -v
```

### Step 4: Run the Backend Server
```bash
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

### Step 5: Start the React Frontend
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 3. Two-Browser Acceptance Walkthrough Script

1. **Window 1 (Trip Leader)**:
   - Register or sign in as `leader@warroom.local` (Password: `Password123!`, Role: `Leader`).
   - Click **Create Trip Room** $\to$ Name: `"Lisbon Retreat"` $\to$ Click **Create**.
   - Copy the generated invite code (e.g., `AB-K9X2`).
2. **Window 2 (Trip Planner)**:
   - Open an incognito browser tab.
   - Register or sign in as `planner@warroom.local` (Role: `Planner`).
   - Click **Join with Code** $\to$ Paste `AB-K9X2` $\to$ Enter room.
3. **Real-Time Board Sync & Concurrency Test**:
   - In Window 1, click **Pin Venue** and pin *"Taberna da Rua das Flores"* to Day 1 (12:00 - 13:30).
   - Window 2 immediately updates in under 50 ms.
   - Simultaneously drag or move the item in both windows with version `v1`:
     - Exactly one window wins and displays `v2`.
     - The second window receives a `trip.board.conflict` toast and rolls back to authoritative server state.
4. **AI Concierge & Honest Hedge Test**:
   - In the right-hand panel, ask: *"Where can we have a vegetarian dinner under 25 euros near Chiado?"*
   - Returns verified venue recommendation with cited grounding evidence and verified DB price.
   - Now ask: *"Where can we have a dinner under 5 euros in Chiado?"*
   - Returns an honest hedge identifying that the **budget** constraint eliminated all venues.
5. **Conflict Detector & Contested Slot Voting**:
   - Pin a second dinner at the exact same hour on Day 1.
   - A schedule overlap banner triggers in red.
   - Click **Open Contested Slot Vote** $\to$ Real-time countdown timer begins.
   - Cast votes in both windows $\to$ Winning item locks automatically; losing item is removed.

---

## 4. Definition-of-Done Tracker

| PRD Requirement | Built In Step | Evidence | Status |
|---|---|---|---|
| Worldwide & Dynamic Currency | Step 5, 6, 11 | `tests/test_global_destinations.py` | Verified (28/28 tests pass) |
| JWT + 4-Role RBAC | Step 3, 4 | `tests/test_rbac.py` | Verified |
| Trip Room + Invite Codes | Step 6 | `routers/trips.py` | Verified |
| Sync < 100 ms, Concurrency Mutex | Step 8, 9 | `tests/test_board.py` | Verified |
| Presence, Chat, Reconnect Grace | Step 9, 10 | `tests/test_ws.py` | Verified |
| Constraint Matcher + Grounded AI | Step 7, 11 | `tests/test_constraints.py`, `tests/test_ai.py` | Verified |
| Conflict Detector + Voting | Step 12, 13 | `concierge/conflicts.py`, `voting.py` | Verified |
| Hamilton-Hare Budget Accuracy 100% | Step 14 | `tests/test_budget.py` (500 property tests) | Verified |
| Recommender P@5 $\ge$ 0.60 | Step 15 | `reco/train.py` (Measured 0.724) | Verified |
| Reconciled Analytics + Admin Upload | Step 16, 17 | `routers/dashboard.py`, `routers/admin.py` | Verified |
| React Collaborative Client | Step 18 | `frontend/src/` | Built & verified |

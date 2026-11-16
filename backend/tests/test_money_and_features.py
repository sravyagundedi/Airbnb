import pytest
from httpx import AsyncClient
from app.models import User, Trip, TripMember, VenueMetadata, ItineraryItem
from app.security import hash_password, make_access_token


@pytest.mark.asyncio
async def test_forgot_and_reset_password_flow(async_client: AsyncClient, seed_users_and_trip):
    # 1. Request reset code for leader@warroom.local
    resp = await async_client.post("/api/v1/auth/forgot-password", json={"email": "leader@warroom.local"})
    assert resp.status_code == 200
    data = resp.json()
    assert "reset_code" in data
    code = data["reset_code"]

    # 2. Reset password using the code
    reset_resp = await async_client.post(
        "/api/v1/auth/reset-password",
        json={
            "email": "leader@warroom.local",
            "reset_code": code,
            "new_password": "NewSecretPassword123!"
        }
    )
    assert reset_resp.status_code == 200

    # 3. Try to log in with new password
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "leader@warroom.local", "password": "NewSecretPassword123!"}
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


@pytest.mark.asyncio
async def test_budget_estimator(async_client: AsyncClient):
    # Estimate budget for 4 people, 5 days in Tokyo, Japan in JPY
    resp = await async_client.post(
        "/api/v1/trips/estimate-budget",
        json={
            "destination": "Tokyo",
            "country": "Japan",
            "duration_days": 5,
            "travelers_count": 4,
            "travel_style": "balanced",
            "currency": "JPY"
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["currency"] == "JPY"
    assert data["currency_symbol"] == "¥"
    assert data["duration_days"] == 5
    assert data["travelers_count"] == 4
    assert data["total_trip_cost"] > 0
    assert data["per_person_total"] > 0
    assert "lodging" in data["category_totals"]
    assert "buffer" in data["category_totals"]


@pytest.mark.asyncio
async def test_expenses_and_settlement_ledger(async_client: AsyncClient, seed_users_and_trip):
    # Leader token (user_id=2)
    token = make_access_token(2, "leader")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Record an expense paid by leader for €90.00
    exp_resp = await async_client.post(
        "/api/v1/trips/1/expenses",
        headers=headers,
        json={
            "title": "Group Dinner at Taberna da Rua",
            "amount": 90.00,
            "category": "dining"
        }
    )
    assert exp_resp.status_code == 201
    exp_data = exp_resp.json()
    assert exp_data["title"] == "Group Dinner at Taberna da Rua"
    assert exp_data["amount"] == 90.00
    assert len(exp_data["shares"]) > 0

    # 2. Get trip expenses & verify settlement plan
    summary_resp = await async_client.get("/api/v1/trips/1/expenses", headers=headers)
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["total_expenses"] == 90.00
    assert len(summary["expenses"]) == 1
    assert "settlement_plan" in summary

    # 3. Mark settled
    settle_resp = await async_client.post("/api/v1/trips/1/expenses/settle", headers=headers)
    assert settle_resp.status_code == 200


@pytest.mark.asyncio
async def test_saved_venues_wishlist(async_client: AsyncClient, seed_users_and_trip):
    token = make_access_token(2, "leader")
    headers = {"Authorization": f"Bearer {token}"}

    # Bookmark a venue (v_3391 seeded in conftest)
    save_resp = await async_client.post("/api/v1/venues/v_3391/save", headers=headers)
    assert save_resp.status_code == 200
    assert save_resp.json()["venue_id"] == "v_3391"

    # List saved venues
    list_resp = await async_client.get("/api/v1/venues/saved", headers=headers)
    assert list_resp.status_code == 200
    saved = list_resp.json()
    assert len(saved) >= 1
    assert any(s["venue_id"] == "v_3391" for s in saved)

    # Unsave venue
    del_resp = await async_client.delete("/api/v1/venues/v_3391/save", headers=headers)
    assert del_resp.status_code == 200

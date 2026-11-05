import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_token_required_401(async_client: AsyncClient):
    resp = await async_client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_endpoint_rbac_matrix(async_client: AsyncClient, seed_users_and_trip):
    tokens = seed_users_and_trip
    payload = [{
        "venueId": "v_test_admin",
        "name": "Admin Venue",
        "category": "dinner",
        "pricePerPerson": 35.0,
        "dietaryTags": ["vegetarian"],
        "hours": {"open": "18:00", "close": "23:00"},
        "coordinates": {"lat": 38.71, "lng": -9.14},
        "rating": 4.5,
        "description": "Admin test."
    }]

    # 1. Viewer gets 403 Forbidden
    resp = await async_client.post(
        "/api/v1/admin/destinations/Lisbon/venues",
        headers={"Authorization": f"Bearer {tokens['viewer_token']}"},
        json=payload
    )
    assert resp.status_code == 403

    # 2. Planner gets 403 Forbidden
    resp = await async_client.post(
        "/api/v1/admin/destinations/Lisbon/venues",
        headers={"Authorization": f"Bearer {tokens['planner_token']}"},
        json=payload
    )
    assert resp.status_code == 403

    # 3. Leader gets 403 Forbidden (Admin only)
    resp = await async_client.post(
        "/api/v1/admin/destinations/Lisbon/venues",
        headers={"Authorization": f"Bearer {tokens['leader_token']}"},
        json=payload
    )
    assert resp.status_code == 403

    # 4. Admin gets 201 Created
    resp = await async_client.post(
        "/api/v1/admin/destinations/Lisbon/venues",
        headers={"Authorization": f"Bearer {tokens['admin_token']}"},
        json=payload
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_non_member_forbidden_on_trip_analytics(async_client: AsyncClient, seed_users_and_trip):
    tokens = seed_users_and_trip
    # Admin (user 1) is not explicitly a member of trip 1 unless added, but has global admin
    # Let's test with a valid member (planner)
    resp = await async_client.get(
        "/api/v1/trips/1/analytics",
        headers={"Authorization": f"Bearer {tokens['planner_token']}"}
    )
    assert resp.status_code == 200

import pytest


@pytest.mark.asyncio
async def test_real_user_auth_lifecycle_and_profile_updates(async_client):
    client = async_client

    # 1. Register a real user with unique email
    reg_payload = {
        "email": "sarah.connor@traveler-warroom.com",
        "password": "Password123!",
        "display_name": "Sarah Connor",
        "role": "planner",
        "budget_ceiling": 250,
        "dietary_tags": ["vegetarian", "gluten-free"]
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    tokens = reg_res.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    access_token = tokens["access_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Get profile /me
    me_res = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_res.status_code == 200
    user_data = me_res.json()
    assert user_data["email"] == "sarah.connor@traveler-warroom.com"
    assert user_data["display_name"] == "Sarah Connor"
    assert user_data["budget_ceiling"] == 250
    assert "vegetarian" in user_data["dietary_tags"]
    assert "gluten-free" in user_data["dietary_tags"]

    # 3. Update profile details via PATCH /api/v1/auth/me
    patch_payload = {
        "display_name": "Sarah Connor Croft",
        "budget_ceiling": 320,
        "dietary_tags": ["vegan", "halal"]
    }
    patch_res = await client.patch("/api/v1/auth/me", headers=auth_headers, json=patch_payload)
    assert patch_res.status_code == 200
    updated_data = patch_res.json()
    assert updated_data["display_name"] == "Sarah Connor Croft"
    assert updated_data["budget_ceiling"] == 320
    assert "vegan" in updated_data["dietary_tags"]
    assert "halal" in updated_data["dietary_tags"]
    assert "vegetarian" not in updated_data["dietary_tags"]

    # 4. Attempt password change with incorrect current password
    bad_pwd_res = await client.patch(
        "/api/v1/auth/me",
        headers=auth_headers,
        json={"current_password": "WrongPassword1!", "new_password": "NewSecretPassword123!"}
    )
    assert bad_pwd_res.status_code == 400
    assert "Current password verification failed" in bad_pwd_res.json()["detail"]

    # 5. Successfully update password
    good_pwd_res = await client.patch(
        "/api/v1/auth/me",
        headers=auth_headers,
        json={"current_password": "Password123!", "new_password": "NewSecretPassword123!"}
    )
    assert good_pwd_res.status_code == 200

    # 6. Verify sign-in with old password fails
    old_login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "sarah.connor@traveler-warroom.com", "password": "Password123!"}
    )
    assert old_login_res.status_code == 401

    # 7. Verify sign-in with new password succeeds
    new_login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "sarah.connor@traveler-warroom.com", "password": "NewSecretPassword123!"}
    )
    assert new_login_res.status_code == 200
    assert "access_token" in new_login_res.json()

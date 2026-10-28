# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>
#
"""Tests for Personal Access Tokens (PATs) and TOTP 2FA authentication."""

import json
import time
from datetime import UTC, datetime, timedelta

import pyotp
import pytest
from sqlalchemy import select

from app.db.models import PersonalAccessToken, Role, User, db


@pytest.fixture(autouse=True)
def ensure_default_roles(app):
    """Ensure basic roles exist for testing."""
    with app.app_context():
        if not Role.query.filter_by(name="user").first():
            db.session.add(Role(name="user"))
            db.session.commit()


@pytest.fixture
def auth_user(client):
    """Register and log in a test user, returning auth headers and user object."""
    email = "pat_totp_user@iqoqo.local"
    password = "SuperSecretPassword123!"
    client.post("/api/auth/register", json={"email": email, "password": password, "display_name": "PAT User"})
    login_res = client.post("/api/auth/login", json={"email": email, "password": password})
    token = json.loads(login_res.data)["token"]
    user = User.query.filter_by(email=email).first()
    return {
        "email": email,
        "password": password,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
        "user_id": str(user.id),
    }


def test_pat_create_and_bearer_auth(client, auth_user):
    """Verify PAT creation, bearer authorization, last_used_at update, and scoping."""
    # 1. Create a PAT
    res = client.post(
        "/api/auth/tokens",
        headers=auth_user["headers"],
        json={"name": "CLI Script", "scopes": ["read:catalog"], "expires_in_days": 30},
    )
    assert res.status_code == 201
    data = json.loads(res.data)
    assert "token" in data
    raw_token = data["token"]
    assert raw_token.startswith("iqo_")
    token_id = data["data"]["id"]
    assert data["data"]["name"] == "CLI Script"
    assert data["data"]["scopes"] == ["read:catalog"]
    assert data["data"]["is_active"] is True

    # 2. Use PAT for GET request (read scope)
    pat_headers = {"Authorization": f"Bearer {raw_token}"}
    profile_res = client.get("/api/profile/", headers=pat_headers)
    assert profile_res.status_code == 200

    # Verify last_used_at updated
    pat = db.session.get(PersonalAccessToken, token_id)
    assert pat.last_used_at is not None

    # 3. Use PAT for POST request without write:catalog scope
    write_res = client.post("/api/items", headers=pat_headers, json={"name": "Forbidden"})
    assert write_res.status_code == 403


def test_pat_pagination_and_revocation(client, auth_user):
    """Verify listing PATs with limit/offset and revoking tokens."""
    # Create two PATs
    res1 = client.post(
        "/api/auth/tokens",
        headers=auth_user["headers"],
        json={"name": "Token 1", "scopes": ["read:catalog", "write:catalog"]},
    )
    token1_data = json.loads(res1.data)
    token1_raw = token1_data["token"]
    token1_id = token1_data["data"]["id"]

    res2 = client.post("/api/auth/tokens", headers=auth_user["headers"], json={"name": "Token 2", "scopes": ["read:catalog"]})
    token2_id = json.loads(res2.data)["data"]["id"]
    assert token2_id is not None

    # List tokens
    list_res = client.get("/api/auth/tokens?limit=1&offset=0", headers=auth_user["headers"])
    assert list_res.status_code == 200
    list_data = json.loads(list_res.data)
    assert len(list_data["items"]) == 1
    assert list_data["total"] >= 2
    assert list_data["limit"] == 1
    assert list_data["offset"] == 0

    # Token 1 works
    assert client.get("/api/profile/", headers={"Authorization": f"Bearer {token1_raw}"}).status_code == 200

    # Revoke Token 1
    del_res = client.delete(f"/api/auth/tokens/{token1_id}", headers=auth_user["headers"])
    assert del_res.status_code == 200

    # Token 1 now returns 401 revoked
    revoked_res = client.get("/api/profile/", headers={"Authorization": f"Bearer {token1_raw}"})
    assert revoked_res.status_code == 401
    assert b"Token revoked" in revoked_res.data


def test_totp_enrollment_verify_and_login_challenge(client, auth_user):
    """Verify TOTP setup flow, login challenge with mfa_required, and recovery code consumption."""
    # 1. Check initial 2FA status
    status_res = client.get("/api/auth/2fa/status", headers=auth_user["headers"])
    assert status_res.status_code == 200
    assert json.loads(status_res.data)["enabled"] is False

    # 2. Enroll 2FA
    enroll_res = client.post("/api/auth/2fa/enroll", headers=auth_user["headers"])
    assert enroll_res.status_code == 200
    enroll_data = json.loads(enroll_res.data)
    assert "secret" in enroll_data
    assert "provisioning_uri" in enroll_data
    assert "qr_code" in enroll_data
    assert len(enroll_data["recovery_codes"]) == 8

    secret = enroll_data["secret"]
    recovery_code = enroll_data["recovery_codes"][0]

    # Verify invalid code fails
    fail_res = client.post("/api/auth/2fa/verify", headers=auth_user["headers"], json={"code": "000000"})
    assert fail_res.status_code == 400

    # Generate valid TOTP code for enrollment
    totp = pyotp.TOTP(secret)
    enrollment_code = totp.at(int(time.time()) - 30)

    # Verify and enable
    enable_res = client.post("/api/auth/2fa/verify", headers=auth_user["headers"], json={"code": enrollment_code})
    assert enable_res.status_code == 200
    assert json.loads(enable_res.data)["enabled"] is True

    # Replay of the enrollment code must fail
    replay_enable = client.post("/api/auth/2fa/verify", headers=auth_user["headers"], json={"code": enrollment_code})
    assert replay_enable.status_code == 400

    # Check status is now enabled
    status_res2 = client.get("/api/auth/2fa/status", headers=auth_user["headers"])
    assert json.loads(status_res2.data)["enabled"] is True

    # Re-enrolling while 2FA is already enabled must return 400 Bad Request
    re_enroll = client.post("/api/auth/2fa/enroll", headers=auth_user["headers"])
    assert re_enroll.status_code == 400
    assert b"2FA is already enabled" in re_enroll.data

    # 3. Test Login Challenge
    # Attempt login without OTP code -> should trigger mfa_required
    login_step1 = client.post(
        "/api/auth/login",
        json={"email": auth_user["email"], "password": auth_user["password"]},
    )
    assert login_step1.status_code == 200
    step1_data = json.loads(login_step1.data)
    assert step1_data.get("mfa_required") is True

    # Login with wrong OTP -> 401
    wrong_otp_res = client.post(
        "/api/auth/login",
        json={"email": auth_user["email"], "password": auth_user["password"], "otp_code": "999999"},
    )
    assert wrong_otp_res.status_code == 401

    # Login with valid recovery code -> 200 and token
    recovery_login_res = client.post(
        "/api/auth/login",
        json={"email": auth_user["email"], "password": auth_user["password"], "otp_code": recovery_code},
    )
    assert recovery_login_res.status_code == 200
    assert "token" in json.loads(recovery_login_res.data)

    # Reusing the same recovery code must fail
    used_recovery_res = client.post(
        "/api/auth/login",
        json={"email": auth_user["email"], "password": auth_user["password"], "otp_code": recovery_code},
    )
    assert used_recovery_res.status_code == 401

    # Login with valid TOTP code -> 200
    valid_code = totp.now()
    valid_totp_login = client.post(
        "/api/auth/login",
        json={"email": auth_user["email"], "password": auth_user["password"], "otp_code": valid_code},
    )
    assert valid_totp_login.status_code == 200
    new_token = json.loads(valid_totp_login.data)["token"]

    # Replay of valid TOTP code within window must fail (anti-replay)
    replay_totp_login = client.post(
        "/api/auth/login",
        json={"email": auth_user["email"], "password": auth_user["password"], "otp_code": valid_code},
    )
    assert replay_totp_login.status_code == 401

    # 4. Disable 2FA with password
    disable_res = client.post(
        "/api/auth/2fa/disable",
        headers={"Authorization": f"Bearer {new_token}"},
        json={"password": auth_user["password"]},
    )
    assert disable_res.status_code == 200
    assert json.loads(disable_res.data)["enabled"] is False

    # Login now works directly without MFA challenge
    direct_login = client.post(
        "/api/auth/login",
        json={"email": auth_user["email"], "password": auth_user["password"]},
    )
    assert direct_login.status_code == 200
    assert "token" in json.loads(direct_login.data)
    assert "mfa_required" not in json.loads(direct_login.data)


def test_pat_cannot_manage_tokens_or_2fa(client, auth_user):
    """Verify Personal Access Tokens cannot access token management or 2FA endpoints."""
    # Create a PAT
    res = client.post(
        "/api/auth/tokens",
        headers=auth_user["headers"],
        json={"name": "Sub-agent Token", "scopes": ["read:catalog", "write:catalog"]},
    )
    assert res.status_code == 201
    pat_token = json.loads(res.data)["token"]
    pat_headers = {"Authorization": f"Bearer {pat_token}"}

    # Attempting to list tokens with PAT -> 403
    assert client.get("/api/auth/tokens", headers=pat_headers).status_code == 403

    # Attempting to create tokens with PAT -> 403
    assert client.post("/api/auth/tokens", headers=pat_headers, json={"name": "Nested"}).status_code == 403

    # Attempting to access 2FA status with PAT -> 403
    assert client.get("/api/auth/2fa/status", headers=pat_headers).status_code == 403

    # Attempting to enroll 2FA with PAT -> 403
    assert client.post("/api/auth/2fa/enroll", headers=pat_headers).status_code == 403


def test_pat_scope_validation_and_admin_bypass_prevention(client, app, auth_user):
    """Verify non-admin cannot mint admin scopes and read:catalog PAT cannot bypass @admin_required."""
    # 1. Non-admin requesting 'admin' or '*' scope -> 403
    res_admin = client.post(
        "/api/auth/tokens",
        headers=auth_user["headers"],
        json={"name": "Hacker Token", "scopes": ["admin"]},
    )
    assert res_admin.status_code == 403
    assert b"Admin scope requires admin role" in res_admin.data

    res_star = client.post(
        "/api/auth/tokens",
        headers=auth_user["headers"],
        json={"name": "Hacker Token Star", "scopes": ["*"]},
    )
    assert res_star.status_code == 403

    # 2. Invalid expires_in_days (0 or negative) -> 400
    res_exp = client.post(
        "/api/auth/tokens",
        headers=auth_user["headers"],
        json={"name": "Bad Expiry", "expires_in_days": 0},
    )
    assert res_exp.status_code == 400

    # 3. Create an admin user and mint both read:catalog and admin PATs
    with app.app_context():
        admin_role = Role.query.filter_by(name="admin").first()
        if not admin_role:
            admin_role = Role(name="admin")
            db.session.add(admin_role)
        admin_user = User(
            email="admin_pat_test@iqoqo.local",
            display_name="Admin PAT User",
            public_username="adminpat",
            is_active=True,
        )
        admin_user.roles.append(admin_role)
        admin_user.set_password("AdminPass1234!")
        db.session.add(admin_user)
        db.session.commit()

    admin_login = client.post(
        "/api/auth/login",
        json={"email": "admin_pat_test@iqoqo.local", "password": "AdminPass1234!"},
    )
    admin_jwt = json.loads(admin_login.data)["token"]
    admin_jwt_headers = {"Authorization": f"Bearer {admin_jwt}"}

    # Admin mints read:catalog PAT
    res_read_pat = client.post(
        "/api/auth/tokens",
        headers=admin_jwt_headers,
        json={"name": "Gemini Reader", "scopes": ["read:catalog"]},
    )
    assert res_read_pat.status_code == 201
    read_pat = json.loads(res_read_pat.data)["token"]
    read_pat_headers = {"Authorization": f"Bearer {read_pat}"}

    # read:catalog PAT on GET /api/admin/stats MUST BE 403
    admin_route_res = client.get("/api/admin/stats", headers=read_pat_headers)
    assert admin_route_res.status_code == 403
    assert b"Admin privileges required" in admin_route_res.data

    # Admin mints admin PAT
    res_admin_pat = client.post(
        "/api/auth/tokens",
        headers=admin_jwt_headers,
        json={"name": "Admin CLI", "scopes": ["admin"]},
    )
    assert res_admin_pat.status_code == 201
    admin_pat = json.loads(res_admin_pat.data)["token"]
    admin_pat_headers = {"Authorization": f"Bearer {admin_pat}"}

    # admin PAT on GET /api/admin/stats MUST BE 200
    admin_route_ok = client.get("/api/admin/stats", headers=admin_pat_headers)
    assert admin_route_ok.status_code == 200

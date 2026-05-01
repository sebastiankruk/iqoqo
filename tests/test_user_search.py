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

import pytest

from app.db.models import User, db


def test_user_search_unauthorized(client):
    """Verify that user search requires authentication."""
    response = client.get("/api/profile/users/search?q=test")
    assert response.status_code == 401


def test_user_search_short_query(client, normal_user_headers):
    """Verify that a query shorter than 2 characters returns empty."""
    response = client.get("/api/profile/users/search?q=a", headers=normal_user_headers)
    assert response.status_code == 200
    assert response.json["data"] == []


def test_user_search_by_email_and_name(client, normal_user_headers, app):
    """Verify searching by email and display name works and excludes the current user."""
    # Create some test users
    with app.app_context():
        # Current user is already created by normal_user_headers fixture

        user1 = User(email="target1@test.local", display_name="Alice Smith", is_active=True)
        user2 = User(email="target2@test.local", display_name="Bob Jones", is_active=True)
        user3 = User(email="target3@test.local", display_name="Charlie Alice", is_active=True)
        inactive = User(email="target4@test.local", display_name="Alice Ghost", is_active=False)
        db.session.add_all([user1, user2, user3, inactive])
        db.session.commit()

    # Search by exact email
    response = client.get("/api/profile/users/search?q=target1@test.local", headers=normal_user_headers)
    assert response.status_code == 200
    data = response.json["data"]
    assert len(data) == 1
    assert data[0]["email"] == "target1@test.local"

    # Search by name "Alice" (should match Alice Smith and Charlie Alice, but not Alice Ghost)
    response = client.get("/api/profile/users/search?q=Alice", headers=normal_user_headers)
    assert response.status_code == 200
    data = response.json["data"]
    assert len(data) == 2
    names = [u["display_name"] for u in data]
    assert "Alice Smith" in names
    assert "Charlie Alice" in names
    assert "Alice Ghost" not in names


def test_user_search_limit(client, normal_user_headers, app):
    """Verify search respects the limit parameter."""
    with app.app_context():
        users = [User(email=f"limit{i}@test.local", display_name=f"Limit Tester {i}", is_active=True) for i in range(15)]
        db.session.add_all(users)
        db.session.commit()

    # Default limit is 10
    response = client.get("/api/profile/users/search?q=Limit", headers=normal_user_headers)
    assert response.status_code == 200
    assert len(response.json["data"]) == 10

    # Custom limit
    response = client.get("/api/profile/users/search?q=Limit&limit=5", headers=normal_user_headers)
    assert response.status_code == 200
    assert len(response.json["data"]) == 5

    # Max limit is 20
    response = client.get("/api/profile/users/search?q=Limit&limit=100", headers=normal_user_headers)
    assert response.status_code == 200
    assert len(response.json["data"]) <= 20

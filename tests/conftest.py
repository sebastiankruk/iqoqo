"""Defines pytest fixtures for the test suite."""

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

# pylint: disable=redefined-outer-name  # pytest fixtures redefine names intentionally

import os

import pytest

os.environ.setdefault("ADMIN_PASSWORD", "test_admin_password")

from app import create_app


@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    from app.db.models import db

    app = create_app(
        config_override={
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


# Global fixtures for admin and normal user headers so tests across modules can reuse them
@pytest.fixture
def admin_headers(app):
    """Fixture to provide authorization headers for an admin user."""
    # Import locally to avoid top-level circular imports during test collection
    from app.api.auth import generate_internal_jwt
    from app.db.models import Permission, Role, User, db

    with app.app_context():
        # Create permissions (including new config/user/role permissions for v0.4.0)
        perms = [
            Permission(name="regenerate:cover"),
            Permission(name="refetch:metadata"),
            Permission(name="delete:item"),
            Permission(name="update:item"),
            Permission(name="read:owners"),
            Permission(name="edit:manifestation"),
            Permission(name="upload:cover"),
            Permission(name="config:external_apis"),
            Permission(name="config:federation"),
            Permission(name="config:affiliate"),
            Permission(name="config:internal"),
            Permission(name="read:users"),
            Permission(name="write:users"),
            Permission(name="read:roles"),
            Permission(name="write:roles"),
        ]
        db.session.add_all(perms)

        # Create admin role
        admin_role = Role(name="admin")
        admin_role.permissions.extend(perms)
        db.session.add(admin_role)

        # Create admin user
        admin_user = User(email="test_admin@iqoqo.local", display_name="Admin")
        admin_user.roles.append(admin_role)
        db.session.add(admin_user)
        db.session.commit()

        # Generate token
        token = generate_internal_jwt(admin_user)
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def normal_user_headers(app):
    """Fixture to provide authorization headers for a normal (non-admin) user."""
    from app.api.auth import generate_internal_jwt
    from app.db.models import Role, User, db

    with app.app_context():
        user_role = Role(name="user")
        db.session.add(user_role)

        user = User(email="test_user@iqoqo.local", display_name="User")
        user.roles.append(user_role)
        db.session.add(user)
        db.session.commit()

        token = generate_internal_jwt(user)
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def vision_user_headers(app):
    """Fixture to provide authorization headers for a user with vision extraction permission."""
    from app.api.auth import generate_internal_jwt
    from app.db.models import Permission, Role, User, db

    with app.app_context():
        # Create permission
        perm = Permission(name="llm_generate:metadata")
        db.session.add(perm)

        # Create role
        vision_role = Role(name="vision_user")
        vision_role.permissions.append(perm)
        db.session.add(vision_role)

        # Create user
        user = User(email="vision_user@iqoqo.local", display_name="Vision User")
        user.roles.append(vision_role)
        db.session.add(user)
        db.session.commit()

        token = generate_internal_jwt(user)
        return {"Authorization": f"Bearer {token}"}

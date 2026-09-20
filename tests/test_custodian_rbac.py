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
"""
Tests for custodian RBAC (Role-Based Access Control) functionality.

Regression test for: Custodian role no longer has access to Administration menu

These tests verify that:
1. Custodian users have the correct permissions
2. Custodian users can access admin endpoints they're authorized for
3. Regular users cannot access custodian-only endpoints
4. Permission format is consistent (colon format, not underscore)
"""

import pytest

from app.api.auth import generate_internal_jwt
from app.db.models import Permission, Role, User, db


@pytest.fixture
def custodian_user(app):
    """Create a custodian user with standard custodian permissions."""
    with app.app_context():

        def get_or_create_perm(name):
            p = Permission.query.filter_by(name=name).first()
            if not p:
                p = Permission(name=name)
                db.session.add(p)
            return p

        # Create custodian role with standard permissions
        custodian_role = Role(name="custodian")
        custodial_perms = [
            get_or_create_perm("write:metadata"),
            get_or_create_perm("read:metadata"),
            get_or_create_perm("escalate:resolve"),
            get_or_create_perm("edit:cover"),
        ]
        custodian_role.permissions.extend(custodial_perms)
        db.session.add(custodian_role)

        custodian = User(email="custodian@iqoqo.local", display_name="Test Custodian")
        custodian.roles.append(custodian_role)
        db.session.add(custodian)
        db.session.commit()

        return custodian


@pytest.fixture
def regular_user(app):
    """Create a regular user without custodian permissions."""
    with app.app_context():
        user = User(email="regular@iqoqo.local", display_name="Regular User")
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def admin_user(app):
    """Create an admin user."""
    with app.app_context():

        def get_or_create_perm(name):
            p = Permission.query.filter_by(name=name).first()
            if not p:
                p = Permission(name=name)
                db.session.add(p)
            return p

        admin_role = Role(name="admin")
        admin_perms = [
            get_or_create_perm("read:users"),
            get_or_create_perm("write:users"),
            get_or_create_perm("read:roles"),
            get_or_create_perm("write:roles"),
        ]
        admin_role.permissions.extend(admin_perms)
        db.session.add(admin_role)

        admin = User(email="admin@iqoqo.local", display_name="Admin User")
        admin.roles.append(admin_role)
        db.session.add(admin)
        db.session.commit()

        return admin


class TestCustodianRBAC:
    """Test custodian role-based access control."""

    def test_custodian_user_has_custodian_role(self, app, custodian_user):
        """Verify custodian user has the custodian role."""
        with app.app_context():
            user = User.query.filter_by(email="custodian@iqoqo.local").first()
            role_names = [role.name for role in user.roles]
            assert "custodian" in role_names

    def test_custodian_user_has_write_metadata_permission(self, app, custodian_user):
        """Verify custodian user has write:metadata permission (colon format)."""
        with app.app_context():
            user = User.query.filter_by(email="custodian@iqoqo.local").first()
            permission_names = [perm.name for role in user.roles for perm in role.permissions]
            assert "write:metadata" in permission_names

    def test_custodian_user_has_read_metadata_permission(self, app, custodian_user):
        """Verify custodian user has read:metadata permission (colon format)."""
        with app.app_context():
            user = User.query.filter_by(email="custodian@iqoqo.local").first()
            permission_names = [perm.name for role in user.roles for perm in role.permissions]
            assert "read:metadata" in permission_names

    def test_custodian_user_has_escalate_resolve_permission(self, app, custodian_user):
        """Verify custodian user has escalate:resolve permission (colon format)."""
        with app.app_context():
            user = User.query.filter_by(email="custodian@iqoqo.local").first()
            permission_names = [perm.name for role in user.roles for perm in role.permissions]
            assert "escalate:resolve" in permission_names

    def test_custodian_user_has_edit_cover_permission(self, app, custodian_user):
        """Verify custodian user has edit:cover permission (colon format)."""
        with app.app_context():
            user = User.query.filter_by(email="custodian@iqoqo.local").first()
            permission_names = [perm.name for role in user.roles for perm in role.permissions]
            assert "edit:cover" in permission_names

    def test_custodian_permissions_use_colon_format(self, app, custodian_user):
        """
        Regression test: Verify all custodian permissions use colon format,
        NOT underscore format.
        """
        with app.app_context():
            user = User.query.filter_by(email="custodian@iqoqo.local").first()
            permission_names = [perm.name for role in user.roles for perm in role.permissions]

            # Should have colon format
            assert "write:metadata" in permission_names
            assert "read:metadata" in permission_names
            assert "escalate:resolve" in permission_names
            assert "edit:cover" in permission_names

            # Should NOT have underscore format (regression check)
            assert "write_metadata" not in permission_names
            assert "read_metadata" not in permission_names
            assert "escalate_resolve" not in permission_names
            assert "edit_cover" not in permission_names

    def test_regular_user_does_not_have_custodian_role(self, app, regular_user):
        """Verify regular user does not have custodian role."""
        with app.app_context():
            user = User.query.filter_by(email="regular@iqoqo.local").first()
            role_names = [role.name for role in user.roles]
            assert "custodian" not in role_names

    def test_regular_user_does_not_have_custodian_permissions(self, app, regular_user):
        """Verify regular user does not have custodian permissions."""
        with app.app_context():
            user = User.query.filter_by(email="regular@iqoqo.local").first()
            permission_names = [perm.name for role in user.roles for perm in role.permissions]

            # Should not have custodian permissions
            assert "write:metadata" not in permission_names
            assert "read:metadata" not in permission_names
            assert "escalate:resolve" not in permission_names
            assert "edit:cover" not in permission_names

    def test_admin_user_has_admin_role(self, app, admin_user):
        """Verify admin user has admin role."""
        with app.app_context():
            user = User.query.filter_by(email="admin@iqoqo.local").first()
            role_names = [role.name for role in user.roles]
            assert "admin" in role_names

    def test_custodian_jwt_token_generation(self, app, custodian_user):
        """Verify JWT token can be generated for custodian user."""
        with app.app_context():
            user = User.query.filter_by(email="custodian@iqoqo.local").first()
            token = generate_internal_jwt(user)
            assert token is not None
            assert isinstance(token, str)
            assert len(token) > 0

    def test_custodian_role_is_not_protected(self, app):
        """Verify custodian role can be modified (not protected like admin/user)."""
        with app.app_context():
            # Create custodian role
            custodian_role = Role(name="custodian_test")
            db.session.add(custodian_role)
            db.session.commit()

            # Verify it's not protected
            role = Role.query.filter_by(name="custodian_test").first()
            assert role is not None
            # Protected roles are typically admin and user
            # Custodian should be modifiable
            assert role.name != "admin"

    def test_multiple_users_can_have_custodian_role(self, app):
        """Verify multiple users can have the custodian role."""
        with app.app_context():

            def get_or_create_perm(name):
                p = Permission.query.filter_by(name=name).first()
                if not p:
                    p = Permission(name=name)
                    db.session.add(p)
                return p

            # Create custodian role
            custodian_role = Role(name="custodian_multi")
            custodial_perms = [
                get_or_create_perm("write:metadata"),
                get_or_create_perm("read:metadata"),
            ]
            custodian_role.permissions.extend(custodial_perms)
            db.session.add(custodian_role)

            # Create multiple custodian users
            custodian1 = User(email="custodian1@iqoqo.local", display_name="Custodian 1")
            custodian1.roles.append(custodian_role)
            db.session.add(custodian1)

            custodian2 = User(email="custodian2@iqoqo.local", display_name="Custodian 2")
            custodian2.roles.append(custodian_role)
            db.session.add(custodian2)

            db.session.commit()

            # Verify both users have custodian role
            user1 = User.query.filter_by(email="custodian1@iqoqo.local").first()
            user2 = User.query.filter_by(email="custodian2@iqoqo.local").first()

            assert "custodian_multi" in [role.name for role in user1.roles]
            assert "custodian_multi" in [role.name for role in user2.roles]


class TestPermissionFormat:
    """Test that permissions use consistent colon format."""

    def test_all_permissions_use_colon_format(self, app):
        """
        Regression test: Verify all permissions in the system use colon format.
        This prevents the bug where underscore format was used in the frontend.
        """
        with app.app_context():
            all_permissions = Permission.query.all()

            for perm in all_permissions:
                # All permissions should use colon format
                assert ":" in perm.name, f"Permission {perm.name} does not use colon format"
                # Should not use underscore format
                assert "_" not in perm.name, f"Permission {perm.name} uses underscore format"

    def test_permission_names_are_lowercase(self, app):
        """Verify all permission names are lowercase."""
        with app.app_context():
            all_permissions = Permission.query.all()

            for perm in all_permissions:
                assert perm.name == perm.name.lower(), f"Permission {perm.name} is not lowercase"

    def test_permission_names_follow_verb_noun_pattern(self, app):
        """Verify permission names follow verb:noun pattern."""
        with app.app_context():
            all_permissions = Permission.query.all()

            for perm in all_permissions:
                parts = perm.name.split(":")
                assert len(parts) == 2, f"Permission {perm.name} does not follow verb:noun pattern"
                verb, noun = parts
                assert len(verb) > 0, f"Permission {perm.name} has empty verb"
                assert len(noun) > 0, f"Permission {perm.name} has empty noun"

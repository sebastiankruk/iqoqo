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
import uuid

from app import create_app
from app.db.models import Item, Permission, Role, User, db

app = create_app()
with app.app_context():
    # 1. Create permissions
    perms = [
        "delete:item",
        "delete:manifestation",
        "update:item",
        "read:owners",
        "regenerate:cover",
        "refetch:metadata",
        "llm_generate:cover",
        "llm_generate:metadata",
        "llm_generate:cloud",
        "upload:cover",
    ]
    for p in perms:
        existing = Permission.query.filter_by(name=p).first()
        if not existing:
            db.session.add(Permission(name=p))
    db.session.commit()

    # 2. Create Roles
    admin_role = Role.query.filter_by(name="admin").first()
    if not admin_role:
        admin_role = Role(name="admin")
        db.session.add(admin_role)

    user_role = Role.query.filter_by(name="user").first()
    if not user_role:
        db.session.add(Role(name="user"))

    admin_role.permissions = Permission.query.all()
    db.session.commit()

    # 3. Create Admin user
    admin_email = app.config.get("ADMIN_EMAIL")
    admin_user = User.query.filter_by(email=admin_email).first()
    if not admin_user:
        admin_user = User(email=admin_email, display_name="Administrator", is_active=True)
        admin_user.set_password(app.config.get("ADMIN_PASSWORD"))
        admin_user.roles.append(admin_role)
        db.session.add(admin_user)
        db.session.commit()
        print(f"Created admin user: {admin_email}")

    # 4. Migrate items to Admin UUID (including those of the legacy system user)
    legacy_items = Item.query.all()
    migrated = 0
    LEGACY_USER_ID = "00000000-0000-4000-a000-000000000000"

    for item in legacy_items:
        # Check if owner_id is not already a valid non-legacy UUID
        owner_id_str = str(item.owner_id)
        should_migrate = False
        try:
            if owner_id_str == LEGACY_USER_ID:
                should_migrate = True
            else:
                uuid.UUID(owner_id_str)
        except (ValueError, TypeError):
            should_migrate = True

        if should_migrate and item.owner_id != admin_user.id:
            item.owner_id = admin_user.id
            migrated += 1

    if migrated > 0:
        db.session.commit()
        print(f"Migrated {migrated} items to admin user.")

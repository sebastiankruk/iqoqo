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
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables before importing models to ensure schema detection works
load_dotenv()

import yaml

from app import create_app
from app.db.models import Item, Permission, Role, User, db
from app.core.permissions import PermissionName

app = create_app()
with app.app_context():
    # 1. Create permissions from shared/permissions.yaml
    permissions_path = Path(app.root_path).parent / "shared" / "permissions.yaml"
    with open(permissions_path, "r") as f:
        permissions_data = yaml.safe_load(f)

    perms = [p["name"] for p in permissions_data.get("permissions", [])]

    # Validate that all permissions in YAML are also in the Enum
    enum_values = {p.value for p in PermissionName}
    for p in perms:
        if p not in enum_values:
            print(f"WARNING: Permission '{p}' found in YAML but not in PermissionName Enum!")

    for p in perms:
        existing = Permission.query.filter_by(name=p).first()
        if not existing:
            db.session.add(Permission(name=p))
        else:
            # Update description if needed (not implemented here but good to have)
            pass
    db.session.commit()

    # 2. Create Roles
    admin_role = Role.query.filter_by(name="admin").first()
    if not admin_role:
        admin_role = Role(name="admin")
        db.session.add(admin_role)

    user_role = Role.query.filter_by(name="user").first()
    if not user_role:
        db.session.add(Role(name="user"))

    contributor_role = Role.query.filter_by(name="contributor").first()
    if not contributor_role:
        contributor_role = Role(name="contributor")
        db.session.add(contributor_role)

    db.session.commit()

    # Admin gets everything
    admin_role.permissions = Permission.query.all()

    # Contributor gets metadata, cover stuff, and llm_generate
    all_perms = Permission.query.all()
    contributor_perms = [
        p for p in all_perms
        if p.name in {
            PermissionName.READ_METADATA.value,
            PermissionName.WRITE_METADATA.value,
            PermissionName.EDIT_COVER.value,
            PermissionName.UPLOAD_COVER.value,
            PermissionName.REGENERATE_COVER.value,
            PermissionName.DELETE_ITEM.value,
        } or p.name.startswith("llm_generate:")
    ]
    contributor_role.permissions = contributor_perms

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

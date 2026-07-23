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
from flask import Flask

# Load environment variables before importing models to ensure schema detection works
load_dotenv()

import yaml

from app import create_app
from app.core.permissions import PermissionName
from app.db.models import Item, Permission, Role, User, db


def run_init_auth(app: Flask | None = None) -> None:
    if app is None:
        app = create_app()

    with app.app_context():
        # 1. Create permissions from shared/permissions.yaml
        permissions_path = Path(app.root_path).parent / "shared" / "permissions.yaml"

        with open(permissions_path, encoding="utf-8") as f:
            permissions_data = yaml.safe_load(f)

        permissions_list = permissions_data.get("permissions", [])

        # Validate that all permissions in YAML are also in the Enum
        enum_values = {p.value for p in PermissionName}
        for p_data in permissions_list:
            name = p_data["name"]
            if name not in enum_values:
                print(f"WARNING: Permission '{name}' found in YAML but not in PermissionName Enum!")

        for p_data in permissions_list:
            name = p_data["name"]
            description = p_data.get("description", "")
            existing = db.session.execute(db.select(Permission).filter_by(name=name)).scalar_one_or_none()
            if not existing:
                db.session.add(Permission(name=name, description=description))
            else:
                if existing.description != description:
                    existing.description = description
                    print(f"Updated description for permission: {name}")
        db.session.commit()

        # 2. Create Roles
        admin_role = db.session.execute(db.select(Role).filter_by(name="admin")).scalar_one_or_none()
        if not admin_role:
            admin_role = Role(name="admin")
            db.session.add(admin_role)

        user_role = db.session.execute(db.select(Role).filter_by(name="user")).scalar_one_or_none()
        if not user_role:
            user_role = Role(name="user")
            db.session.add(user_role)

        contributor_role = db.session.execute(db.select(Role).filter_by(name="contributor")).scalar_one_or_none()
        if not contributor_role:
            contributor_role = Role(name="contributor")
            db.session.add(contributor_role)

        db.session.commit()

        # Admin gets everything
        admin_role.permissions = db.session.execute(db.select(Permission)).scalars().all()

        # Contributor gets metadata, llm_generate, delete item, edit:cover, and escalate:resolve
        all_perms = db.session.execute(db.select(Permission)).scalars().all()
        contributor_perms = [
            p
            for p in all_perms
            if p.name.endswith(":metadata")
            or p.name == PermissionName.EDIT_COVER.value
            or p.name.startswith("llm_generate:")
            or p.name == PermissionName.DELETE_ITEM.value
            or p.name == PermissionName.ESCALATE_RESOLVE.value
        ]
        contributor_role.permissions = contributor_perms

        # Standard User gets permissions to interact with items and basic tasks
        user_perm_names = {
            PermissionName.WRITE_ITEM.value,
            PermissionName.UPDATE_ITEM.value,
            PermissionName.DELETE_ITEM.value,
            PermissionName.READ_METADATA.value,
            PermissionName.UPLOAD_COVER.value,
            PermissionName.REGENERATE_COVER.value,
            PermissionName.REFETCH_COVER.value,
            PermissionName.LLM_GENERATE_METADATA.value,
            PermissionName.LLM_GENERATE_COVER.value,
            PermissionName.ESCALATE_REQUEST.value,
        }
        user_role.permissions = [p for p in all_perms if p.name in user_perm_names]

        db.session.commit()

        # 3. Create Admin user
        admin_email = str(app.config.get("ADMIN_EMAIL") or "")
        admin_user = db.session.execute(db.select(User).filter_by(email=admin_email)).scalar_one_or_none()
        if not admin_user:
            admin_user = User(email=admin_email, display_name="Administrator", is_active=True)
            admin_password = str(app.config.get("ADMIN_PASSWORD") or "")
            admin_user.set_password(admin_password)
            if admin_role is not None:
                admin_user.roles.append(admin_role)
            db.session.add(admin_user)
            db.session.commit()
            print(f"Created admin user: {admin_email}")

        # 4. Migrate items to Admin UUID (including those of the legacy system user)
        legacy_items = db.session.execute(db.select(Item)).scalars().all()
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


if __name__ == "__main__":
    run_init_auth()

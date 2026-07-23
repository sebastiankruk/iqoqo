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

"""Dedicated script to sync permissions and default roles without clobbering."""

from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

# Load environment variables before importing models to ensure schema detection works
load_dotenv()

import yaml

from app import create_app
from app.core.permissions import PermissionName
from app.db.models import Permission, Role, db


def run_sync_permissions(app: Flask | None = None) -> None:
    if app is None:
        app = create_app()

    with app.app_context():
        # 1. Sync permissions from shared/permissions.yaml
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

        # 2. Sync Roles (Create if missing)
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

        # 3. Add default permissions to roles without clobbering existing ones
        all_perms = db.session.execute(db.select(Permission)).scalars().all()

        # Admin gets all permissions
        for p in all_perms:
            if p not in admin_role.permissions:
                admin_role.permissions.append(p)

        # Contributor gets metadata, llm_generate, delete item, edit:cover, and escalate:resolve
        for p in all_perms:
            is_contrib_perm = (
                p.name.endswith(":metadata")
                or p.name == PermissionName.EDIT_COVER.value
                or p.name.startswith("llm_generate:")
                or p.name == PermissionName.DELETE_ITEM.value
                or p.name == PermissionName.ESCALATE_RESOLVE.value
            )
            if is_contrib_perm and p not in contributor_role.permissions:
                contributor_role.permissions.append(p)

        # Standard User gets permissions to interact with items, basic tasks, and escalate:request
        user_perm_names = {
            PermissionName.WRITE_ITEM.value,
            PermissionName.UPDATE_ITEM.value,
            PermissionName.DELETE_ITEM.value,
            PermissionName.READ_METADATA.value,
            PermissionName.UPLOAD_COVER.value,
            PermissionName.REGENERATE_COVER.value,
            PermissionName.LLM_GENERATE_METADATA.value,
            PermissionName.LLM_GENERATE_COVER.value,
            PermissionName.ESCALATE_REQUEST.value,
        }
        for p in all_perms:
            if p.name in user_perm_names and p not in user_role.permissions:
                user_role.permissions.append(p)

        db.session.commit()
        print("Permissions and roles synced successfully.")


if __name__ == "__main__":
    run_sync_permissions()

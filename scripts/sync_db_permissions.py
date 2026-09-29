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
from app.core.permissions import RoleName, resolve_role_permissions
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

        # 2. Ensure every built-in role exists.
        #
        # MOD-OPS-13: which permissions a role receives is no longer decided
        # here. `RoleName` and `ROLE_PERMISSION_PATTERNS` are generated into
        # app/core/permissions.py from the `roles:` section of
        # shared/permissions.yaml, so there is exactly one definition to keep
        # correct. This function only reconciles the database against it.
        roles: dict[str, Role] = {}
        # Named `role_enum` rather than `role_name`: the loop below reuses the
        # plain-string role name, and reusing one name for a RoleName and then
        # a str is a type error mypy is right to reject.
        for role_enum in RoleName:
            role = db.session.execute(db.select(Role).filter_by(name=role_enum.value)).scalar_one_or_none()
            if not role:
                role = Role(name=role_enum.value)
                db.session.add(role)
            roles[role_enum.value] = role

        db.session.commit()

        # 3. Grant each role its permissions, without removing anything an
        #    administrator added by hand.
        #
        #    Patterns are resolved against the permissions actually present in
        #    the database, not against the PermissionName enum. A permission an
        #    admin added by hand is therefore still granted wherever its name
        #    matches a pattern.
        all_perms = db.session.execute(db.select(Permission)).scalars().all()
        by_name = {p.name: p for p in all_perms}

        for role_name, role in roles.items():
            granted = resolve_role_permissions(role_name, by_name.keys())
            added = 0
            for perm_name in sorted(granted):
                perm = by_name[perm_name]
                if perm not in role.permissions:
                    role.permissions.append(perm)
                    added += 1
            print(f"Role '{role_name}': {len(granted)} permission(s) granted ({added} newly added).")

        db.session.commit()
        print("Permissions and roles synced successfully.")


if __name__ == "__main__":
    run_sync_permissions()

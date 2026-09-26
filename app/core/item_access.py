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
Shared ownership enforcement for physical `/api/items/<id>` endpoints.

`verify_item_ownership()` / `require_item_access()` centralize the strict
"is this user the owner (or an admin)?" check used by mutation-adjacent
endpoints (delete, QR code generation) for physical Item records.

Wishlist entries (UserWorkIntent) are managed through the dedicated
``/api/wishlist`` blueprint and have their own authorization logic.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from functools import wraps

from flask import g, jsonify

from app.db.models import Item, User, db


def _is_admin(user: User | None) -> bool:
    return bool(user) and any(role.name == "admin" for role in getattr(user, "roles", []))


def verify_item_ownership(item_id: int, user_id: uuid.UUID) -> bool:
    """
    Strict owner-or-admin gate for a physical ``item_id``.

    Only positive IDs resolve to ``Item`` (physical holdings). Returns False
    -- never raises -- when the referenced row does not exist, so callers can
    uniformly respond with 404 without a separate existence check.
    """
    user = db.session.get(User, user_id)
    is_admin = _is_admin(user)

    item = db.session.get(Item, item_id)
    if not item:
        return False
    return is_admin or str(item.owner_id) == str(user_id)


def require_item_access(bola: bool = False) -> Callable:
    """
    Decorator enforcing `verify_item_ownership()` for view functions that
    accept an `item_id` (or `id`) path parameter.

    Must be stacked *below* `@require_auth` (it relies on `g.user_id` already
    being populated; it does not perform authentication itself).

    `bola=True` responds 404 "Item not found" for an existing-but-forbidden
    item as well as a missing one, hiding whether the id exists at all
    (Broken Object Level Authorization protection) -- appropriate for
    read-like endpoints such as QR code generation. `bola=False` (default)
    responds 403 "Forbidden" for an existing-but-forbidden item, matching the
    existing mutation (update/delete) convention.
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated(*args, **kwargs):
            user_id = getattr(g, "user_id", None)
            if not user_id:
                return jsonify({"success": False, "data": None, "error": "Authentication required"}), 401

            raw_id = kwargs.get("item_id", kwargs.get("id"))
            if raw_id is None:
                raise TypeError("require_item_access() requires an 'item_id' or 'id' path parameter")
            item_id = int(raw_id)

            record = db.session.get(Item, item_id)
            if record is None:
                return jsonify({"success": False, "data": None, "error": "Item not found"}), 404

            if not verify_item_ownership(item_id, user_id):
                if bola:
                    return jsonify({"success": False, "data": None, "error": "Item not found"}), 404
                return jsonify({"success": False, "data": None, "error": "Forbidden"}), 403

            return f(*args, **kwargs)

        return decorated

    return decorator

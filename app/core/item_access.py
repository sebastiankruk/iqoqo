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
from typing import Any

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


def is_item_publicly_visible(item: Item | dict[str, Any]) -> bool:
    """Determine whether an item is visible to public, unauthenticated callers.

    Checks:
    1. Item's explicit `is_hidden` property (must be False).
    2. Item's explicit `is_public` property if present (must be True).
    3. Item's `default_item_visibility` from the owner user account:
       If the owner has default_item_visibility == 'private', items default to private
       unless explicitly overridden.
    4. FederationConsent: If federated_collection is explicitly False, items are omitted
       from public federation snapshots.

    Args:
        item: Item model or dictionary representation.

    Returns:
        bool: True if item is publicly visible, False otherwise.
    """
    if isinstance(item, dict):
        if item.get("is_hidden") is True:
            return False
        if "is_public" in item and item["is_public"] is False:
            return False
        owner_id = item.get("owner_id")
    else:
        if getattr(item, "is_hidden", False) is True:
            return False
        if hasattr(item, "is_public") and item.is_public is False:
            return False
        owner_id = getattr(item, "owner_id", None)

    if owner_id:
        user_uuid = owner_id if isinstance(owner_id, uuid.UUID) else uuid.UUID(str(owner_id))
        user = db.session.get(User, user_uuid)
        if user:
            # Check owner default visibility
            if getattr(user, "default_item_visibility", "public") == "private":
                # For dictionaries, check if explicit is_public was provided as True
                if isinstance(item, dict) and item.get("is_public") is True:
                    pass
                elif not isinstance(item, dict) and getattr(item, "is_hidden", False) is False and "is_public" in getattr(item, "meta", {}):
                    # Check if explicit is_public was set in meta
                    if item.meta.get("is_public") is True:
                        pass
                    else:
                        return False
                else:
                    return False

            # Check federation consent for collection exposure
            from app.db.federation import FederationConsent

            consent = db.session.execute(db.select(FederationConsent).where(FederationConsent.user_id == user.id)).scalars().first()
            if consent and not consent.federated_collection:
                return False

    return True


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

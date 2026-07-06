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
Shared ownership enforcement for the polymorphic `/api/items/<id>` surface.

iQoQo routes wishlist ("virtual") items through the same numeric id space as
physical holdings by encoding them as a negative id (`id = -intent_id`; see
`app/api/items.py::_get_virtual_item_detail`). Because a single integer can
therefore resolve to either an `Item` or a `UserWorkIntent` depending on its
sign, any endpoint that authorizes access with an inline `id > 0` assumption
(or that forgets to check the negative-id branch at all) is vulnerable to an
IDOR (Insecure Direct Object Reference): a caller could pass another user's
`-intent_id` and read/mutate a resource that isn't theirs.

`verify_item_ownership()` / `require_item_access()` centralize the strict
"is this user the owner (or an admin)?" check used by mutation-adjacent
endpoints (delete, QR code generation). They deliberately do NOT encode the
broader, endpoint-specific read semantics used by `GET /api/items/<id>`
(anonymous browsing of non-hidden physical items, borrower access, the
`read:owners` permission, wishlist entries visible to any authenticated user
unless the owner hides them) -- those rules differ enough between the two
branches that a single generic helper would either over-grant or under-grant
access. See `_get_physical_item_detail()` / `_get_virtual_item_detail()`.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from functools import wraps

from flask import g, jsonify

from app.db.models import Item, User, UserWorkIntent, db


def _is_admin(user: User | None) -> bool:
    return bool(user) and any(role.name == "admin" for role in getattr(user, "roles", []))


def verify_item_ownership(item_id: int, user_id: uuid.UUID) -> bool:
    """
    Strict owner-or-admin gate for a signed `item_id`.

    Negative ids resolve to `UserWorkIntent` (wishlist entries); positive ids
    resolve to `Item` (physical holdings). Returns False -- never raises --
    when the referenced row does not exist, so callers can uniformly respond
    with 404 without a separate existence check.
    """
    user = db.session.get(User, user_id)
    is_admin = _is_admin(user)

    if item_id < 0:
        intent = db.session.get(UserWorkIntent, -item_id)
        if not intent:
            return False
        return is_admin or str(intent.user_id) == str(user_id)

    item = db.session.get(Item, item_id)
    if not item:
        return False
    return is_admin or str(item.owner_id) == str(user_id)


def require_item_access(bola: bool = False) -> Callable:
    """
    Decorator enforcing `verify_item_ownership()` for view functions that
    accept a signed `item_id` (or `id`) path parameter.

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

            record = db.session.get(UserWorkIntent, -item_id) if item_id < 0 else db.session.get(Item, item_id)
            if record is None:
                return jsonify({"success": False, "data": None, "error": "Item not found"}), 404

            if not verify_item_ownership(item_id, user_id):
                if bola:
                    return jsonify({"success": False, "data": None, "error": "Item not found"}), 404
                return jsonify({"success": False, "data": None, "error": "Forbidden"}), 403

            return f(*args, **kwargs)

        return decorated

    return decorator

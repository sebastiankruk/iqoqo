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
"""Service for privileged, atomic Item ownership reassignment.

Manages preview computation, deterministic fingerprinting, and transactional
execution of physical Item transfers with immutable custody logging and
source-owned collection link cleanup.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select

from app.db.core import Item, ItemCustodyEvent, UserCollection, UserCollectionItem
from app.db.models import User, db


class ReassignmentError(Exception):
    """Base error for item reassignment operations."""


class ReassignmentValidationError(ReassignmentError):
    """Raised when input validation, permissions, or scope rules fail."""


class ReassignmentConflictError(ReassignmentError):
    """Raised when preview fingerprint, count, or concurrent changes conflict."""


def compute_reassignment_fingerprint(
    mode: str,
    source_user_id: uuid.UUID | str,
    target_user_id: uuid.UUID | str,
    item_ids: list[int],
) -> str:
    """
    Computes a canonical SHA-256 fingerprint over normalized reassignment parameters.
    """
    sorted_ids_str = ",".join(str(i) for i in sorted(item_ids))
    normalized = f"{mode}:{str(source_user_id)}:{str(target_user_id)}:{sorted_ids_str}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def record_transfer_event(
    item_id: int,
    from_owner_id: uuid.UUID | str | None,
    to_owner_id: uuid.UUID | str | None,
    actor_id: uuid.UUID | str | None = None,
    notes: str | None = None,
) -> ItemCustodyEvent:
    """
    Creates and records an immutable ItemCustodyEvent of type 'transfer'.
    """
    event = ItemCustodyEvent(
        item_id=item_id,
        actor_id=uuid.UUID(str(actor_id)) if actor_id else None,
        from_owner_id=uuid.UUID(str(from_owner_id)) if from_owner_id else None,
        to_owner_id=uuid.UUID(str(to_owner_id)) if to_owner_id else None,
        event_type="transfer",
        notes=notes,
        recorded_at=datetime.now(UTC),
    )
    db.session.add(event)
    return event


def _resolve_and_validate_users(
    source_user_id: Any,
    target_user_id: Any,
) -> tuple[User, User]:
    """Resolves and validates source and target user records."""
    try:
        s_uuid = uuid.UUID(str(source_user_id))
    except (ValueError, TypeError) as exc:
        raise ReassignmentValidationError("Invalid source user identifier") from exc

    try:
        t_uuid = uuid.UUID(str(target_user_id))
    except (ValueError, TypeError) as exc:
        raise ReassignmentValidationError("Invalid target user identifier") from exc

    if s_uuid == t_uuid:
        raise ReassignmentValidationError("Source and target accounts must be different")

    source = db.session.get(User, s_uuid)
    if not source:
        raise ReassignmentValidationError("Source user account not found")

    target = db.session.get(User, t_uuid)
    if not target:
        raise ReassignmentValidationError("Target user account not found")

    if not target.is_active:
        raise ReassignmentValidationError("Target user account is inactive")

    return source, target


def preview_reassignment(
    source_user_id: Any,
    target_user_id: Any,
    mode: str,
    item_ids: list[int] | None = None,
) -> dict[str, Any]:
    """
    Computes a server preview for an item reassignment operation.

    Validates identities and scope, gathers matching physical items, checks
    hidden/lent distributions, and returns a deterministic fingerprint.
    """
    source, target = _resolve_and_validate_users(source_user_id, target_user_id)

    if mode not in ("single", "selected", "all"):
        raise ReassignmentValidationError(f"Invalid mode '{mode}'. Must be single, selected, or all.")

    if mode == "single":
        if not item_ids or len(item_ids) != 1:
            raise ReassignmentValidationError("Mode 'single' requires exactly one item ID")
        item_id = item_ids[0]
        if not isinstance(item_id, int) or item_id <= 0:
            raise ReassignmentValidationError("Item ID must be a positive integer")

        item = db.session.get(Item, item_id)
        if not item or item.owner_id != source.id:
            raise ReassignmentValidationError("Requested item does not exist or is not owned by source account")
        matching_items = [item]

    elif mode == "selected":
        if not item_ids:
            raise ReassignmentValidationError("Mode 'selected' requires at least one item ID")

        # Validate unique positive physical IDs
        unique_ids = set()
        for i in item_ids:
            if not isinstance(i, int) or i <= 0:
                raise ReassignmentValidationError("All item IDs must be positive integers")
            unique_ids.add(i)

        stmt = select(Item).where(Item.id.in_(unique_ids))
        found_items = db.session.execute(stmt).scalars().all()

        if len(found_items) != len(unique_ids):
            raise ReassignmentValidationError("One or more selected items were not found")

        for it in found_items:
            if it.owner_id != source.id:
                raise ReassignmentValidationError("One or more selected items are not owned by source account")

        matching_items = list(found_items)

    else:  # mode == "all"
        stmt = select(Item).where(Item.owner_id == source.id)
        matching_items = list(db.session.execute(stmt).scalars().all())

    matching_ids = [it.id for it in matching_items]
    hidden_count = sum(1 for it in matching_items if getattr(it, "is_hidden", False))
    lent_count = sum(1 for it in matching_items if getattr(it, "collection_status", None) == "lent")

    fingerprint = compute_reassignment_fingerprint(
        mode=mode,
        source_user_id=source.id,
        target_user_id=target.id,
        item_ids=matching_ids,
    )

    return {
        "source": {
            "id": str(source.id),
            "username": getattr(source, "username", None) or source.email,
            "display_name": source.display_name or source.email,
        },
        "target": {
            "id": str(target.id),
            "username": getattr(target, "username", None) or target.email,
            "display_name": target.display_name or target.email,
        },
        "mode": mode,
        "item_ids": sorted(matching_ids),
        "total_count": len(matching_ids),
        "hidden_count": hidden_count,
        "lent_count": lent_count,
        "fingerprint": fingerprint,
    }


def execute_reassignment(
    source_user_id: Any,
    target_user_id: Any,
    mode: str,
    expected_fingerprint: str,
    expected_count: int,
    item_ids: list[int] | None = None,
    actor_id: Any = None,
) -> dict[str, Any]:
    """
    Executes atomic ownership reassignment within a single database transaction.

    Locks rows, re-validates fingerprint and current ownership, cleans up source-owned
    personal collection links, transfers Item.owner_id, and appends an immutable
    transfer custody event per Item.
    """
    source, target = _resolve_and_validate_users(source_user_id, target_user_id)

    if mode not in ("single", "selected", "all"):
        raise ReassignmentValidationError(f"Invalid mode '{mode}'.")

    # Lock rows and fetch current items
    if mode == "single":
        if not item_ids or len(item_ids) != 1:
            raise ReassignmentValidationError("Mode 'single' requires exactly one item ID")
        stmt = select(Item).where(Item.id == item_ids[0], Item.owner_id == source.id).with_for_update()
        items = list(db.session.execute(stmt).scalars().all())

    elif mode == "selected":
        if not item_ids:
            raise ReassignmentValidationError("Mode 'selected' requires item IDs")
        stmt = select(Item).where(Item.id.in_(set(item_ids)), Item.owner_id == source.id).with_for_update()
        items = list(db.session.execute(stmt).scalars().all())

    else:  # mode == "all"
        stmt = select(Item).where(Item.owner_id == source.id).with_for_update()
        items = list(db.session.execute(stmt).scalars().all())

    actual_ids = [it.id for it in items]

    if len(items) != expected_count:
        raise ReassignmentConflictError(f"Item count mismatch: expected {expected_count}, but found {len(items)}. Scope may have changed.")

    actual_fingerprint = compute_reassignment_fingerprint(
        mode=mode,
        source_user_id=source.id,
        target_user_id=target.id,
        item_ids=actual_ids,
    )

    if actual_fingerprint != expected_fingerprint:
        raise ReassignmentConflictError("Preview fingerprint mismatch: item selection has changed.")

    if not items:
        # Zero items matching scope
        return {
            "success": True,
            "transferred_count": 0,
            "source_id": str(source.id),
            "target_id": str(target.id),
            "mode": mode,
        }

    # 1. Clean up source-owned personal collection links
    source_coll_ids = select(UserCollection.id).where(UserCollection.owner_id == source.id)
    db.session.execute(
        delete(UserCollectionItem).where(
            UserCollectionItem.item_id.in_(actual_ids),
            UserCollectionItem.collection_id.in_(source_coll_ids),
        )
    )

    # 2. Update Item ownership and append custody transfer events
    actor_uuid = uuid.UUID(str(actor_id)) if actor_id else None
    for it in items:
        it.owner_id = target.id
        record_transfer_event(
            item_id=it.id,
            from_owner_id=source.id,
            to_owner_id=target.id,
            actor_id=actor_uuid,
            notes=f"Reassigned from user {source.id} to {target.id}",
        )

    db.session.commit()

    return {
        "success": True,
        "transferred_count": len(items),
        "source_id": str(source.id),
        "target_id": str(target.id),
        "mode": mode,
    }

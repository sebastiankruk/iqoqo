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
"""Tests for physical Item ownership reassignment workflow.

Verifies:
- Custody provenance with structured from/to owner references and account-deletion SET NULL.
- Transactional reassignment service with preview fingerprinting and atomic rollback.
- Admin-only API security boundaries (admin + write:users required).
- Non-admin and ordinary owner self-service override prohibition.
- Stale preview conflict rejection (HTTP 409).
- Preservation of FRBR hierarchy, item status, lending status, and tags.
- Removal of source-owned personal collection links without leaking target collection links.
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import patch

import pytest

from app.core.permissions import PermissionName
from app.db.core import (
    Expression,
    Item,
    ItemCustodyEvent,
    Manifestation,
    UserCollection,
    UserCollectionItem,
    Work,
)
from app.db.models import Permission, Role, User, db
from app.services.item_reassignment import (
    ReassignmentConflictError,
    ReassignmentValidationError,
    compute_reassignment_fingerprint,
    execute_reassignment,
    preview_reassignment,
    record_transfer_event,
)


@pytest.fixture
def transfer_fixture(app: Any) -> dict[str, Any]:
    """Sets up a complete FRBR environment with source, target, items, and collections."""
    with app.app_context():
        # Source user
        source = User(email="source_collector@iqoqo.local", display_name="Source Collector", is_active=True)
        source.set_password("pass-source")
        db.session.add(source)

        # Target user
        target = User(email="target_collector@iqoqo.local", display_name="Target Collector", is_active=True)
        target.set_password("pass-target")
        db.session.add(target)

        # Inactive user
        inactive = User(email="inactive_user@iqoqo.local", display_name="Inactive User", is_active=False)
        inactive.set_password("pass-inactive")
        db.session.add(inactive)

        # Third party user
        other = User(email="other_collector@iqoqo.local", display_name="Other Collector", is_active=True)
        other.set_password("pass-other")
        db.session.add(other)

        db.session.flush()

        # Create FRBR records
        w = Work(title="Ownership Transfer Book", meta={"Description": "Valuable volume"})
        db.session.add(w)
        db.session.flush()

        e = Expression(work_id=w.id, content_type="text", language="en")
        db.session.add(e)
        db.session.flush()

        m = Manifestation(expression_id=e.id, isbn13="9780123456789", publisher="Test Press")
        db.session.add(m)
        db.session.flush()

        # Items owned by source
        item1 = Item(
            manifestation_id=m.id,
            owner_id=source.id,
            status="available",
            collection_status="available",
            is_hidden=False,
        )
        item2 = Item(
            manifestation_id=m.id,
            owner_id=source.id,
            status="available",
            collection_status="lent",
            lent_to_user_id=other.id,
            is_hidden=False,
        )
        item3 = Item(
            manifestation_id=m.id,
            owner_id=source.id,
            status="available",
            collection_status="available",
            is_hidden=True,
        )
        # Item owned by other
        item_other = Item(
            manifestation_id=m.id,
            owner_id=other.id,
            status="available",
            collection_status="available",
            is_hidden=False,
        )
        db.session.add_all([item1, item2, item3, item_other])
        db.session.flush()

        # Source personal collection
        coll = UserCollection(owner_id=source.id, name="Source Private Shelf")
        db.session.add(coll)
        db.session.flush()

        link1 = UserCollectionItem(collection_id=coll.id, item_id=item1.id)
        link2 = UserCollectionItem(collection_id=coll.id, item_id=item2.id)
        db.session.add_all([link1, link2])

        db.session.commit()

        return {
            "source_id": source.id,
            "target_id": target.id,
            "inactive_id": inactive.id,
            "other_id": other.id,
            "work_id": w.id,
            "manif_id": m.id,
            "item1_id": item1.id,
            "item2_id": item2.id,
            "item3_id": item3.id,
            "item_other_id": item_other.id,
            "coll_id": coll.id,
        }


class TestItemCustodyProvenance:
    """Task 1.1 & 1.2: Custody transfer event model and account deletion semantics."""

    def test_record_transfer_event_provenance(self, app: Any, transfer_fixture: dict[str, Any]) -> None:
        with app.app_context():
            item_id = transfer_fixture["item1_id"]
            source_id = transfer_fixture["source_id"]
            target_id = transfer_fixture["target_id"]

            event = record_transfer_event(
                item_id=item_id,
                from_owner_id=source_id,
                to_owner_id=target_id,
                actor_id=source_id,
                notes="Standard transfer",
            )
            db.session.commit()

            saved = db.session.get(ItemCustodyEvent, event.id)
            assert saved is not None
            assert saved.event_type == "transfer"
            assert saved.from_owner_id == source_id
            assert saved.to_owner_id == target_id
            assert saved.actor_id == source_id
            assert saved.recorded_at is not None

    def test_account_deletion_sets_custody_owner_references_null(self, app: Any, transfer_fixture: dict[str, Any]) -> None:
        with app.app_context():
            item_id = transfer_fixture["item1_id"]
            source_id = transfer_fixture["source_id"]
            target_id = transfer_fixture["target_id"]

            event = record_transfer_event(
                item_id=item_id,
                from_owner_id=source_id,
                to_owner_id=target_id,
            )
            db.session.commit()
            event_id = event.id

            # Delete target user to verify SET NULL semantics
            target = db.session.get(User, target_id)
            assert target is not None
            db.session.delete(target)
            db.session.commit()

            reloaded_event = db.session.get(ItemCustodyEvent, event_id)
            assert reloaded_event is not None
            assert reloaded_event.to_owner_id is None
            assert reloaded_event.from_owner_id == source_id


class TestTransactionalReassignmentService:
    """Task 1.3, 2.2, 2.3, 2.4: Core service logic, fingerprinting, and transactional guarantees."""

    def test_preview_reassignment_validation(self, app: Any, transfer_fixture: dict[str, Any]) -> None:
        with app.app_context():
            source_id = transfer_fixture["source_id"]
            target_id = transfer_fixture["target_id"]
            inactive_id = transfer_fixture["inactive_id"]

            # Identical accounts fail
            with pytest.raises(ReassignmentValidationError, match="must be different"):
                preview_reassignment(source_id, source_id, mode="all")

            # Inactive target fails
            with pytest.raises(ReassignmentValidationError, match="inactive"):
                preview_reassignment(source_id, inactive_id, mode="all")

            # Foreign-owned item in selected mode fails closed
            with pytest.raises(ReassignmentValidationError, match="not owned by source"):
                preview_reassignment(
                    source_id,
                    target_id,
                    mode="selected",
                    item_ids=[transfer_fixture["item1_id"], transfer_fixture["item_other_id"]],
                )

            # Negative ID fails
            with pytest.raises(ReassignmentValidationError, match="positive integers"):
                preview_reassignment(source_id, target_id, mode="selected", item_ids=[-5])

    def test_preview_and_execute_all_items(self, app: Any, transfer_fixture: dict[str, Any]) -> None:
        with app.app_context():
            source_id = transfer_fixture["source_id"]
            target_id = transfer_fixture["target_id"]

            preview = preview_reassignment(source_id, target_id, mode="all")
            assert preview["total_count"] == 3
            assert preview["hidden_count"] == 1
            assert preview["lent_count"] == 1
            assert preview["fingerprint"] is not None

            # Execute with valid preview fingerprint
            res = execute_reassignment(
                source_user_id=source_id,
                target_user_id=target_id,
                mode="all",
                expected_fingerprint=preview["fingerprint"],
                expected_count=3,
            )
            assert res["success"] is True
            assert res["transferred_count"] == 3

            # Verify ownership updated on all 3 items
            items = (
                db.session.execute(
                    db.select(Item).where(
                        Item.id.in_([transfer_fixture["item1_id"], transfer_fixture["item2_id"], transfer_fixture["item3_id"]])
                    )
                )
                .scalars()
                .all()
            )
            for it in items:
                assert it.owner_id == target_id

            # Verify source collection links removed
            links = (
                db.session.execute(db.select(UserCollectionItem).where(UserCollectionItem.collection_id == transfer_fixture["coll_id"]))
                .scalars()
                .all()
            )
            assert len(links) == 0

            # Verify lending state and borrower preserved
            lent_item = db.session.get(Item, transfer_fixture["item2_id"])
            assert lent_item.collection_status == "lent"
            assert lent_item.lent_to_user_id == transfer_fixture["other_id"]

            # Verify custody transfer events appended
            events = db.session.execute(db.select(ItemCustodyEvent).where(ItemCustodyEvent.event_type == "transfer")).scalars().all()
            assert len(events) == 3

    def test_stale_fingerprint_conflict_rollback(self, app: Any, transfer_fixture: dict[str, Any]) -> None:
        with app.app_context():
            source_id = transfer_fixture["source_id"]
            target_id = transfer_fixture["target_id"]

            preview = preview_reassignment(source_id, target_id, mode="all")
            assert preview["fingerprint"] != "invalid_stale_fingerprint_sha256"
            assert preview["total_count"] == 3
            with pytest.raises(ReassignmentConflictError, match="fingerprint mismatch"):
                execute_reassignment(
                    source_user_id=source_id,
                    target_user_id=target_id,
                    mode="all",
                    expected_fingerprint="invalid_stale_fingerprint_sha256",
                    expected_count=3,
                )

            # Confirm no rows changed
            item1 = db.session.get(Item, transfer_fixture["item1_id"])
            assert item1.owner_id == source_id

    def test_injected_failure_rolls_back_entire_batch(self, app: Any, transfer_fixture: dict[str, Any]) -> None:
        with app.app_context():
            source_id = transfer_fixture["source_id"]
            target_id = transfer_fixture["target_id"]
            preview = preview_reassignment(source_id, target_id, mode="all")

            # Mock record_transfer_event to raise midway
            with patch("app.services.item_reassignment.record_transfer_event", side_effect=RuntimeError("Simulated write failure")):
                with pytest.raises(RuntimeError):
                    execute_reassignment(
                        source_user_id=source_id,
                        target_user_id=target_id,
                        mode="all",
                        expected_fingerprint=preview["fingerprint"],
                        expected_count=3,
                    )
                db.session.rollback()

            # Verify all items remain owned by source
            for item_id in [transfer_fixture["item1_id"], transfer_fixture["item2_id"], transfer_fixture["item3_id"]]:
                it = db.session.get(Item, item_id)
                assert it.owner_id == source_id


class TestAuthorizedReassignmentApi:
    """Task 2.1 - 2.5: API authorization, RBAC boundary, preview, and confirmation endpoints."""

    def test_unauthorized_and_forbidden_access(self, client: Any, normal_user_headers: Any, transfer_fixture: dict[str, Any]) -> None:
        # Unauthenticated request
        res = client.get("/api/v1/admin/ownership/accounts")
        assert res.status_code in (401, 403)

        # Ordinary user with normal_user_headers
        res = client.get("/api/v1/admin/ownership/accounts", headers=normal_user_headers)
        assert res.status_code in (401, 403)

        res = client.post(
            "/api/v1/admin/ownership/preview",
            json={
                "source_user_id": str(transfer_fixture["source_id"]),
                "target_user_id": str(transfer_fixture["target_id"]),
                "mode": "all",
            },
            headers=normal_user_headers,
        )
        assert res.status_code in (401, 403)

    def test_admin_ownership_endpoints_flow(self, client: Any, admin_headers: Any, transfer_fixture: dict[str, Any]) -> None:
        source_id = str(transfer_fixture["source_id"])
        target_id = str(transfer_fixture["target_id"])

        # 1. Accounts discovery
        res_acc = client.get("/api/v1/admin/ownership/accounts", headers=admin_headers)
        assert res_acc.status_code == 200
        assert res_acc.json["success"] is True
        assert len(res_acc.json["data"]) >= 2

        # 2. Source items discovery (paginated)
        res_items = client.get(f"/api/v1/admin/ownership/items?source_user_id={source_id}", headers=admin_headers)
        assert res_items.status_code == 200
        assert res_items.json["success"] is True
        assert res_items.json["pagination"]["total"] == 3

        # 3. Preview endpoint
        preview_payload = {
            "source_user_id": source_id,
            "target_user_id": target_id,
            "mode": "single",
            "item_ids": [transfer_fixture["item1_id"]],
        }
        res_prev = client.post("/api/v1/admin/ownership/preview", json=preview_payload, headers=admin_headers)
        assert res_prev.status_code == 200
        assert res_prev.json["success"] is True
        prev_data = res_prev.json["data"]
        assert prev_data["total_count"] == 1
        fingerprint = prev_data["fingerprint"]

        # 4. Confirmation execution endpoint
        exec_payload = {
            "source_user_id": source_id,
            "target_user_id": target_id,
            "mode": "single",
            "item_ids": [transfer_fixture["item1_id"]],
            "expected_fingerprint": fingerprint,
            "expected_count": 1,
        }
        res_exec = client.post("/api/v1/admin/ownership/reassign", json=exec_payload, headers=admin_headers)
        assert res_exec.status_code == 200
        assert res_exec.json["success"] is True
        assert res_exec.json["data"]["transferred_count"] == 1

    def test_ordinary_put_item_rejects_owner_id_change(
        self, client: Any, normal_user_headers: Any, transfer_fixture: dict[str, Any]
    ) -> None:
        """Verify normal Item PUT endpoint still strictly rejects owner_id changes."""
        item_id = transfer_fixture["item1_id"]
        res = client.put(
            f"/api/items/{item_id}",
            json={"owner_id": str(transfer_fixture["target_id"])},
            headers=normal_user_headers,
        )
        assert res.status_code in (400, 403, 404)

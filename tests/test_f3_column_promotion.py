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
"""Regression tests for FRBR F3 Column Promotion (ISBN-13, Publisher, Format Type)."""

from typing import Any

import pytest
from pydantic import ValidationError

from app.api.schemas import ManifestationFrbrUpdateSchema, ManifestationUpdateSchema
from app.core.frbr_service import (
    create_expression,
    create_manifestation,
    create_work,
    get_or_create_book_manifestation,
    update_manifestation,
)
from app.db.models import Manifestation, db


class TestManifestationTypedColumns:
    """Test explicit typed column declarations on Manifestation model."""

    def test_column_attributes_exist(self, app: Any) -> None:
        """Verify explicit typed columns are declared on Manifestation."""
        with app.app_context():
            assert hasattr(Manifestation, "isbn13")
            assert hasattr(Manifestation, "publisher")
            assert hasattr(Manifestation, "format_type")
            assert hasattr(Manifestation, "format")

            # Check column lengths
            pub_col = Manifestation.publisher.property.columns[0]
            fmt_col = Manifestation.format_type.property.columns[0]
            assert pub_col.type.length == 255
            assert fmt_col.type.length == 50


class TestFrbrServicePhysicalAttributes:
    """Test service layer column-first reads, writes, and meta pruning."""

    def test_create_manifestation_direct_arguments(self, app: Any) -> None:
        """Verify direct column arguments are persisted and not injected into meta."""
        with app.app_context():
            work = create_work("Direct Column Test")
            expr = create_expression(work.id, content_type="text")
            manif = create_manifestation(
                expr.id,
                isbn13="978-0-14-044913-6",
                publisher="Penguin Books",
                format_type="Paperback",
            )

            assert manif.isbn13 == "9780140449136"
            assert manif.publisher == "Penguin Books"
            assert manif.format_type == "paperback"
            assert manif.format == "paperback"

            # Verify meta is clean of promoted keys
            meta = manif.meta or {}
            assert "isbn13" not in meta
            assert "isbn" not in meta
            assert "publisher" not in meta
            assert "Publisher" not in meta
            assert "format_type" not in meta

    def test_create_manifestation_meta_backfill_and_pruning(self, app: Any) -> None:
        """Verify legacy keys in meta are promoted to columns and pruned from meta dict."""
        with app.app_context():
            work = create_work("Meta Backfill Test")
            expr = create_expression(work.id, content_type="text")
            manif = create_manifestation(
                expr.id,
                meta={
                    "isbn": "978-1-56619-909-4",
                    "Publisher": "Dover Publications",
                    "format_type": "Hardcover",
                    "extra_note": "First edition",
                },
            )

            assert manif.isbn13 == "9781566199094"
            assert manif.publisher == "Dover Publications"
            assert manif.format_type == "hardcover"
            assert manif.format == "hardcover"

            # Non-promoted keys must remain intact
            assert manif.meta == {"extra_note": "First edition"}

    def test_update_manifestation_updates_columns_and_prunes(self, app: Any) -> None:
        """Verify update_manifestation updates typed columns and strips promoted keys."""
        with app.app_context():
            work = create_work("Update Column Test")
            expr = create_expression(work.id, content_type="sound")
            manif = create_manifestation(expr.id)

            update_manifestation(
                manif.id,
                publisher="Blue Note Records",
                format_type="Vinyl",
                meta={"format_type": "Vinyl", "publisher": "Blue Note Records", "pressing": "180g"},
            )

            db.session.refresh(manif)
            assert manif.publisher == "Blue Note Records"
            assert manif.format_type == "vinyl"
            assert "publisher" not in (manif.meta or {})
            assert "format_type" not in (manif.meta or {})
            assert (manif.meta or {}).get("pressing") == "180g"

    def test_get_or_create_book_manifestation_typed_storage(self, app: Any) -> None:
        """Verify get_or_create_book_manifestation populates and queries typed columns."""
        with app.app_context():
            isbn = "978-0-345-33970-6"
            manif = get_or_create_book_manifestation(
                isbn=isbn,
                title="The Fellowship of the Ring",
                authors=["J.R.R. Tolkien"],
                publisher="Ballantine Books",
            )
            assert manif is not None
            assert manif.isbn13 == "9780345339706"
            assert manif.publisher == "Ballantine Books"
            assert manif.format_type == "book"

            # Query again by raw formatted ISBN; should find existing
            manif_again = get_or_create_book_manifestation(
                isbn="9780345339706",
                title="The Fellowship of the Ring",
            )
            assert manif_again is not None
            assert manif_again.id == manif.id


class TestApiSerializersAndSchemas:
    """Test API response contracts and Pydantic schema validation."""

    def test_get_manifestation_detail_exposes_typed_attributes(self, client: Any, app: Any) -> None:
        """Verify GET /api/manifestations/<id> surfaces format_type and format."""
        with app.app_context():
            work = create_work("Detail API Test")
            expr = create_expression(work.id, content_type="text")
            manif = create_manifestation(
                expr.id,
                isbn13="9780132350884",
                publisher="Prentice Hall",
                format_type="paperback",
            )

            resp = client.get(f"/api/manifestations/{manif.id}")
            assert resp.status_code == 200
            data = resp.get_json()["data"]
            assert data["isbn13"] == "9780132350884"
            assert data["publisher"] == "Prentice Hall"
            assert data["format_type"] == "paperback"
            assert data["format"] == "paperback"

    def test_get_manifestations_list_exposes_typed_attributes(self, client: Any, app: Any) -> None:
        """Verify GET /api/manifestations list serializer includes format_type."""
        with app.app_context():
            work = create_work("List API Test")
            expr = create_expression(work.id, content_type="text")
            manif = create_manifestation(
                expr.id,
                isbn13="9780201616224",
                publisher="Addison-Wesley",
                format_type="hardcover",
            )

            resp = client.get("/api/manifestations?limit=50")
            assert resp.status_code == 200
            items = resp.get_json()["data"]
            entry = next((i for i in items if i["id"] == manif.id), None)
            assert entry is not None
            assert entry["isbn13"] == "9780201616224"
            assert entry["publisher"] == "Addison-Wesley"
            assert entry["format_type"] == "hardcover"
            assert entry["format"] == "hardcover"

    def test_schemas_validation_and_length_limits(self) -> None:
        """Verify Pydantic schemas enforce type limits on physical attributes."""
        # Valid
        s1 = ManifestationUpdateSchema(publisher="Valid Publisher", format_type="paperback")
        assert s1.publisher == "Valid Publisher"
        assert s1.format_type == "paperback"

        s2 = ManifestationFrbrUpdateSchema(publisher="Valid Pub", format_type="hardcover")
        assert s2.publisher == "Valid Pub"
        assert s2.format_type == "hardcover"

        # Publisher max length 255
        with pytest.raises(ValidationError):
            ManifestationUpdateSchema(publisher="A" * 256)

        with pytest.raises(ValidationError):
            ManifestationFrbrUpdateSchema(publisher="A" * 256)

        # Format type max length 50
        with pytest.raises(ValidationError):
            ManifestationUpdateSchema(format_type="B" * 51)

        with pytest.raises(ValidationError):
            ManifestationFrbrUpdateSchema(format_type="B" * 51)

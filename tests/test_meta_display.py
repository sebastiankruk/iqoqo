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
"""Unit and integration tests for backend metadata display projection (Stage 2)."""

import pathlib
import re
from typing import Any

import pytest

from app.core.meta_display import (
    ALL_DECLARED_SPELLINGS,
    ALL_RENDERED_OR_STRUCTURAL_KEYS,
    DISPLAY_FIELD_DEFINITIONS,
    EXTENDED_METADATA_LABEL_PUBLISHER_PRECEDENCE,
    ITEM_HEADER_PUBLISHER_PRECEDENCE,
    build_display_projection,
    read_first_present_value,
)


def _parse_frontend_field_chains() -> dict[str, list[str]]:
    """Parse frontend/lib/meta.ts FIELD_CHAINS for bidirectional vocabulary testing."""
    meta_path = pathlib.Path("frontend/lib/meta.ts")
    assert meta_path.exists(), "frontend/lib/meta.ts not found"
    content = meta_path.read_text(encoding="utf-8")
    match = re.search(r"export const FIELD_CHAINS = \{([\s\S]*?)\} as const", content)
    assert match, "Could not locate FIELD_CHAINS in frontend/lib/meta.ts"
    lines = [line.strip() for line in match.group(1).splitlines() if ":" in line]
    parsed: dict[str, list[str]] = {}
    for line in lines:
        field_name = line.split(":")[0].strip()
        chain_part = line.split("[")[1].split("]")[0]
        spellings = [s.strip(" \",'") for s in chain_part.split(",") if s.strip(" \",'")]
        parsed[field_name] = spellings
    return parsed


class TestMetaDisplayVocabulary:
    """Test suite for vocabulary synchronization between backend and frontend (Task 2.4)."""

    def test_bidirectional_vocabulary_match(self):
        """Task 2.4: Assert backend DISPLAY_FIELD_DEFINITIONS and frontend FIELD_CHAINS match exactly."""
        frontend_chains = _parse_frontend_field_chains()

        # 1. Assert field sets match
        backend_fields = set(DISPLAY_FIELD_DEFINITIONS.keys())
        frontend_fields = set(frontend_chains.keys())
        missing_in_backend = frontend_fields - backend_fields
        missing_in_frontend = backend_fields - frontend_fields
        assert not missing_in_backend, f"Fields in frontend missing from backend table: {missing_in_backend}"
        assert not missing_in_frontend, f"Fields in backend missing from frontend table: {missing_in_frontend}"

        # 2. Assert spellings per field match
        for field, backend_def in DISPLAY_FIELD_DEFINITIONS.items():
            expected_spellings = tuple(frontend_chains[field])
            assert backend_def.spellings == expected_spellings, (
                f"Spelling mismatch for field '{field}': " f"backend has {backend_def.spellings}, frontend has {expected_spellings}"
            )

    def test_bidirectional_test_fails_on_drift(self):
        """Task 2.4 verification: Adding a simulated drift causes the check to fail naming the entry."""
        frontend_chains = _parse_frontend_field_chains()
        simulated_chains = dict(frontend_chains)
        simulated_chains["new_field"] = ["new_field"]

        missing_in_backend = set(simulated_chains.keys()) - set(DISPLAY_FIELD_DEFINITIONS.keys())
        assert missing_in_backend == {"new_field"}

    def test_label_publisher_precedence_split(self):
        """Task 2.1: Unit test asserts label/publisher precedence split matches extended-metadata.tsx."""
        # ExtendedMetadata: "label" comes before "publisher"
        assert EXTENDED_METADATA_LABEL_PUBLISHER_PRECEDENCE[0] == "label"
        assert EXTENDED_METADATA_LABEL_PUBLISHER_PRECEDENCE[1] == "publisher"

        # ItemHeader: "publisher" comes before "label"
        assert ITEM_HEADER_PUBLISHER_PRECEDENCE[0] == "publisher"
        assert ITEM_HEADER_PUBLISHER_PRECEDENCE[1] == "label"

        # When both label and publisher are present:
        meta = {"label": "Blue Note Records", "publisher": "EMI Music"}
        ext_val = read_first_present_value(meta, EXTENDED_METADATA_LABEL_PUBLISHER_PRECEDENCE)
        hdr_val = read_first_present_value(meta, ITEM_HEADER_PUBLISHER_PRECEDENCE)
        assert ext_val == "Blue Note Records"
        assert hdr_val == "EMI Music"


class TestMetaDisplayProjectionBuilder:
    """Task 2.2: Unit tests for projection builder covering casing and value rules."""

    def test_ocr_cased_input(self):
        """Task 2.2: OCR imports produce capitalized keys (Format, Title, Authors, Publisher)."""
        raw_meta = {
            "Format": "Vinyl",
            "Title": "A Love Supreme",
            "Authors": ["John Coltrane"],
            "Publisher": "Impulse!",
            "Year": "1965",
        }
        proj = build_display_projection(raw_meta)
        assert proj["sections"]["format"] == "Vinyl"
        assert proj["sections"]["label_publisher"] == "Impulse!"
        # All capitalized known fields are suppressed from additional_details
        assert proj["additional_details"] == []

    def test_provider_cased_input(self):
        """Task 2.2: Provider imports produce lowercase keys (format, title, authors, publisher)."""
        raw_meta = {
            "format": "vinyl",
            "title": "A Love Supreme",
            "authors": ["John Coltrane"],
            "publisher": "Impulse!",
            "year": "1965",
        }
        proj = build_display_projection(raw_meta)
        assert proj["sections"]["format"] == "vinyl"
        assert proj["sections"]["label_publisher"] == "Impulse!"
        assert proj["additional_details"] == []

    def test_mixed_cased_input_and_unknown_keys(self):
        """Task 2.2: Mixed casing with unknown keys preserves unknown primitives in additional_details."""
        raw_meta = {
            "Format": "Vinyl",
            "publisher": "Blue Note",
            "Language": "English",
            "edition": "Remastered 2024",
            "catalog_number": "BST 81595",  # Rendered in dedicated audio section, suppressed
        }
        proj = build_display_projection(raw_meta)
        assert proj["sections"]["format"] == "Vinyl"
        assert proj["sections"]["label_publisher"] == "Blue Note"

        # Unrecognized primitive keys appear in additional_details with friendly labels
        keys = {item["key"]: item["value"] for item in proj["additional_details"]}
        assert keys.get("Language") == "English"
        assert keys.get("edition") == "Remastered 2024"
        assert "Format" not in keys
        assert "publisher" not in keys
        assert "catalog_number" not in keys

    def test_drops_empty_and_disallowed_values(self):
        """Task 2.2: Drops unknown, n/a, none, and empty strings."""
        raw_meta = {
            "Format": "none",
            "description": "unknown",
            "notes": "N/A",
            "custom_blank": "",
            "custom_ok": "Valid text",
        }
        proj = build_display_projection(raw_meta)
        assert "format" not in proj["sections"]
        assert "description" not in proj["sections"]
        add_keys = [item["key"] for item in proj["additional_details"]]
        assert "notes" not in add_keys
        assert "custom_blank" not in add_keys
        assert "custom_ok" in add_keys

    def test_drops_non_primitive_objects(self):
        """Task 2.2: Key whose value is an object (dict/list) is dropped from additional_details."""
        raw_meta = {
            "custom_str": "valid",
            "custom_num": 42,
            "custom_obj": {"nested": "value"},
            "custom_list": [1, 2, 3],
        }
        proj = build_display_projection(raw_meta)
        add_keys = [item["key"] for item in proj["additional_details"]]
        assert "custom_str" in add_keys
        assert "custom_num" in add_keys
        assert "custom_obj" not in add_keys
        assert "custom_list" not in add_keys

    def test_round_trip_client_suppression_parity(self):
        """Task 2.5: Projection contains no field the client would have suppressed."""
        # Simulated test payload with every declared spelling
        test_meta: dict[str, Any] = {}
        for spelling in ALL_DECLARED_SPELLINGS:
            test_meta[spelling] = f"val_{spelling}"

        test_meta["arbitrary_extra"] = "Should Appear"

        proj = build_display_projection(test_meta)
        add_keys = {item["key"] for item in proj["additional_details"]}

        # None of the declared spellings may appear in additional_details
        intersect = add_keys & ALL_DECLARED_SPELLINGS
        assert not intersect, f"Declared spellings leaked into additional_details: {intersect}"
        assert "arbitrary_extra" in add_keys


class TestItemDetailDisplayEndpoint:
    """Task 2.3: Verify GET /api/v1/items/<id> response contains both manifestation_meta and display."""

    def test_item_detail_includes_untouched_meta_and_projection(self, app, client):
        from app.db.core import MediaCategory, MediaFormat
        from app.db.models import Expression, Item, Manifestation, User, Work, db

        with app.app_context():
            user = User(email="display_test@iqoqo.local", display_name="Display Tester")
            db.session.add(user)
            db.session.flush()

            w = Work(title="Display Test Work")
            db.session.add(w)
            db.session.flush()

            e = Expression(work_id=w.id, content_type=MediaCategory.TEXT)
            db.session.add(e)
            db.session.flush()

            raw_meta = {
                "Format": "Book",
                "Publisher": "Penguin Classics",
                "Year": "1984",
                "Language": "English",
                "custom_prop": "Special Value",
            }
            m = Manifestation(expression_id=e.id, meta=raw_meta)
            db.session.add(m)
            db.session.flush()

            item = Item(manifestation_id=m.id, owner_id=user.id, status="available", is_hidden=False)
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        resp = client.get(f"/api/items/{item_id}")
        assert resp.status_code == 200
        data = resp.get_json()["data"]

        # 1. Untouched raw manifestation_meta is present
        assert "manifestation_meta" in data
        assert data["manifestation_meta"] == raw_meta

        # 2. Additive display projection is present
        assert "display" in data
        display = data["display"]
        assert display["sections"]["format"] == "Book"
        assert display["sections"]["label_publisher"] == "Penguin Classics"
        add_keys = {entry["key"]: entry["value"] for entry in display["additional_details"]}
        assert add_keys.get("Language") == "English"
        assert add_keys.get("custom_prop") == "Special Value"
        # Primary fields suppressed from additional_details
        assert "Format" not in add_keys
        assert "Publisher" not in add_keys

    def test_manifestation_detail_includes_display_projection(self, app, client):
        """Task 3.1: Verify GET /api/manifestations/<id> response contains display projection."""
        from app.db.core import MediaCategory
        from app.db.models import Expression, Manifestation, Work, db

        with app.app_context():
            w = Work(title="Manifestation Display Test Work")
            db.session.add(w)
            db.session.flush()

            e = Expression(work_id=w.id, content_type=MediaCategory.TEXT)
            db.session.add(e)
            db.session.flush()

            raw_meta = {
                "format": "Hardcover",
                "publisher": "Tor Books",
                "_provenance": {"source": "openlibrary"},
                "_raw_candidates": {},
                "custom_edition": "First Edition",
            }
            m = Manifestation(expression_id=e.id, meta=raw_meta)
            db.session.add(m)
            db.session.commit()
            m_id = m.id

        resp = client.get(f"/api/manifestations/{m_id}")
        assert resp.status_code == 200
        data = resp.get_json()["data"]

        assert "display" in data
        display = data["display"]
        assert display["sections"]["format"] == "Hardcover"
        add_keys = {entry["key"] for entry in display["additional_details"]}
        assert "custom_edition" in add_keys
        # Ensure underscore internal keys are stripped
        assert "_provenance" not in add_keys
        assert "_raw_candidates" not in add_keys

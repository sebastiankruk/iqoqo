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
"""Tests for FRBR author normalization and contribution synchronization.

Verifies:
- `normalize_authors_list` helper handles strings, stringified JSON arrays, unicode escapes, and delimiters.
- `update_work` synchronizes `work.meta["authors"]` with `WorkContribution` rows in both directions.
- Manifestation API endpoints return sanitized `authors` lists even when raw `work.meta` is malformed.
- `scripts/repair_frbr_authors.py` functions cleanly in `--dry-run` and `--apply` modes.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from app.core.frbr_service import normalize_authors_list, update_work
from app.db.contributions import Contributor
from app.db.models import Expression, Manifestation, Work, WorkContribution, db
from scripts.repair_frbr_authors import repair_work_authors


class TestNormalizeAuthorsList:
    """Unit tests for normalize_authors_list."""

    def test_handles_none_and_empty(self) -> None:
        assert normalize_authors_list(None) == []
        assert normalize_authors_list("") == []
        assert normalize_authors_list("   ") == []
        assert normalize_authors_list([]) == []
        assert normalize_authors_list([None, ""]) == []

    def test_handles_single_author_string(self) -> None:
        assert normalize_authors_list("Remigiusz Mróz") == ["Remigiusz Mróz"]
        assert normalize_authors_list("  Stephen King  ") == ["Stephen King"]

    def test_handles_comma_and_semicolon_delimited_strings(self) -> None:
        assert normalize_authors_list("Author One, Author Two") == ["Author One", "Author Two"]
        assert normalize_authors_list("Author One; Author Two; Author Three") == [
            "Author One",
            "Author Two",
            "Author Three",
        ]
        assert normalize_authors_list("Author One, Author Two; Author Three") == [
            "Author One",
            "Author Two",
            "Author Three",
        ]

    def test_handles_json_encoded_string_array(self) -> None:
        encoded = '["Remigiusz Mróz", "Stephen King"]'
        assert normalize_authors_list(encoded) == ["Remigiusz Mróz", "Stephen King"]

    def test_handles_escaped_unicode_characters(self) -> None:
        escaped_json = '["Remigiusz Mr\\u00f3z"]'
        assert normalize_authors_list(escaped_json) == ["Remigiusz Mróz"]

        escaped_plain = "Remigiusz Mr\\u00f3z"
        assert normalize_authors_list(escaped_plain) == ["Remigiusz Mróz"]

    def test_handles_existing_python_list(self) -> None:
        assert normalize_authors_list(["Remigiusz Mróz", "Stephen King"]) == [
            "Remigiusz Mróz",
            "Stephen King",
        ]
        assert normalize_authors_list(["  Author A  ", "Author B  ", None, ""]) == [
            "Author A",
            "Author B",
        ]

    def test_handles_dict_with_name_key(self) -> None:
        assert normalize_authors_list([{"name": "Remigiusz Mróz"}, {"title": "Stephen King"}]) == [
            "Remigiusz Mróz",
            "Stephen King",
        ]


class TestWorkAuthorSynchronization:
    """Integration tests for Work metadata and WorkContribution synchronization."""

    def test_update_work_with_authors_in_meta_syncs_contributions(self, app: Any) -> None:
        with app.app_context():
            work = Work(title="Test Book", meta={"authors": ["Original Author"]})
            db.session.add(work)
            db.session.commit()

            # Update work via meta["authors"] as raw string (simulating frontend edit)
            updated = update_work(work.id, meta={"authors": "Remigiusz Mróz"})

            assert updated is not None
            assert updated.meta["authors"] == ["Remigiusz Mróz"]

            # Verify relational WorkContribution row was created
            contributions = WorkContribution.query.filter_by(work_id=work.id).all()
            assert len(contributions) == 1
            assert contributions[0].contributor.name == "Remigiusz Mróz"
            assert contributions[0].role == "author"

    def test_update_work_with_contributions_backfills_meta_authors(self, app: Any) -> None:
        with app.app_context():
            work = Work(title="Test Book 2", meta={})
            db.session.add(work)
            db.session.commit()

            # Update work via contributions payload
            updated = update_work(
                work.id,
                contributions=[
                    {"name": "Ursula K. Le Guin", "role": "author"},
                    {"name": "Translator Person", "role": "translator"},
                ],
            )

            assert updated is not None
            assert updated.meta["authors"] == ["Ursula K. Le Guin"]

            contributions = WorkContribution.query.filter_by(work_id=work.id).all()
            assert len(contributions) == 2
            roles = {c.role for c in contributions}
            assert "author" in roles
            assert "translator" in roles


class TestManifestationApiAuthorResilience:
    """Test manifestation endpoints return list of authors even with corrupted work.meta."""

    def test_manifestation_endpoints_with_malformed_author_meta(self, client: Any, app: Any) -> None:
        with app.app_context():
            # Inject a work with malformed raw string author in meta
            work = Work(title="Malformed Work", meta={"authors": '["Remigiusz Mr\\u00f3z"]'})
            db.session.add(work)
            db.session.flush()

            expression = Expression(work_id=work.id, content_type="text", language="pl", meta={})
            db.session.add(expression)
            db.session.flush()

            manifestation = Manifestation(
                expression_id=expression.id,
                isbn13="9788380753235",
                meta={"Title": "Test Manifestation"},
            )
            db.session.add(manifestation)
            db.session.commit()
            m_id = manifestation.id

        # GET /api/manifestations
        res = client.get("/api/manifestations")
        assert res.status_code == 200
        data = res.get_json()
        item = next((m for m in data["data"] if m["id"] == m_id), None)
        assert item is not None
        assert item["authors"] == ["Remigiusz Mróz"]
        assert isinstance(item["authors"], list)

        # GET /api/manifestations/<id>
        res_detail = client.get(f"/api/manifestations/{m_id}")
        assert res_detail.status_code == 200
        detail_data = res_detail.get_json()["data"]
        assert detail_data["authors"] == ["Remigiusz Mróz"]
        assert isinstance(detail_data["authors"], list)


class TestRepairFrbrAuthorsScript:
    """Test the data repair script for legacy corrupted authors."""

    def test_repair_script_dry_run_and_apply(self, app: Any) -> None:
        with app.app_context():
            # Create a work with raw corrupted author string
            work = Work(title="Script Test Work", meta={"authors": "Corrupted, String"})
            db.session.add(work)
            db.session.commit()
            w_id = work.id

            # Run dry-run
            inspected, repaired = repair_work_authors(apply_changes=False)
            assert inspected >= 1
            assert repaired >= 1

            # Work in DB should still be un-applied
            db.session.expire_all()
            work_check = db.session.get(Work, w_id)
            assert work_check.meta["authors"] == "Corrupted, String"

            # Run apply
            inspected_apply, repaired_apply = repair_work_authors(apply_changes=True)
            assert inspected_apply >= 1
            assert repaired_apply >= 1

            # Work in DB should now be normalized list and have contributions
            db.session.expire_all()
            work_fixed = db.session.get(Work, w_id)
            assert work_fixed.meta["authors"] == ["Corrupted", "String"]

            contribs = WorkContribution.query.filter_by(work_id=w_id).all()
            names = {c.contributor.name for c in contribs}
            assert names == {"Corrupted", "String"}

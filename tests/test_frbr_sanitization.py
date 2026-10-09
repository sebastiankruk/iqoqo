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
"""Tests for FRBR description metadata sanitization via bleach."""

from __future__ import annotations

from typing import Any

import pytest

from app.core.frbr_service import (
    _merge_metadata,
    create_expression,
    create_manifestation,
    create_work,
    sanitize_metadata_description,
    update_expression,
    update_manifestation,
    update_work,
)
from app.db.models import Expression, Manifestation, Work, db


class TestFrbrSanitization:
    """Unit tests for metadata description sanitization."""

    def test_sanitize_metadata_description_neutralizes_xss(self) -> None:
        meta = {
            "description": '<p>Safe description</p><script>alert("xss")</script><iframe src="evil.com"></iframe>',
        }
        sanitized = sanitize_metadata_description(meta)
        assert sanitized is not None
        assert "<script>" not in sanitized["description"]
        assert "</script>" not in sanitized["description"]
        assert "<iframe>" not in sanitized["description"]
        assert "</iframe>" not in sanitized["description"]
        assert "<p>Safe description</p>" in sanitized["description"]

    def test_sanitize_metadata_description_preserves_allowed_tags(self) -> None:
        meta = {
            "description": (
                '<p>This is <b>bold</b> and <i>italic</i> with <a href="https://iqoqo.cc">link</a>. ' "<ul><li>Item 1</li></ul></p>"
            ),
        }
        sanitized = sanitize_metadata_description(meta)
        assert sanitized is not None
        assert "<b>bold</b>" in sanitized["description"]
        assert "<i>italic</i>" in sanitized["description"]
        assert '<a href="https://iqoqo.cc">link</a>' in sanitized["description"]
        assert "<ul><li>Item 1</li></ul>" in sanitized["description"]

    def test_sanitize_metadata_description_case_insensitive(self) -> None:
        meta = {
            "Description": 'Dangerous <img src=x onerror=alert(1)> and <a href="javascript:alert(1)">bad link</a>',
        }
        sanitized = sanitize_metadata_description(meta)
        assert sanitized is not None
        assert "<img" not in sanitized["Description"]
        assert "javascript:" not in sanitized["Description"]

    def test_sanitize_metadata_description_none_or_empty(self) -> None:
        assert sanitize_metadata_description(None) is None
        assert sanitize_metadata_description({}) == {}
        assert sanitize_metadata_description({"title": "Test"}) == {"title": "Test"}

    def test_create_work_sanitizes_description(self, app: Any) -> None:
        with app.app_context():
            work = create_work(
                title="Sanitization Test Book",
                meta={"description": "Good <script>evil()</script><b>Great</b>"},
            )
            assert "<script>" not in (work.meta or {}).get("description", "")
            assert "<b>Great</b>" in (work.meta or {}).get("description", "")

    def test_update_work_sanitizes_description(self, app: Any) -> None:
        with app.app_context():
            work = create_work(title="Update Sanitization Test", meta={})
            updated = update_work(
                work.id,
                meta={"description": "<svg onload=alert(1)><em>Safe emphasis</em>"},
            )
            assert "<svg" not in (updated.meta or {}).get("description", "")
            assert "<em>Safe emphasis</em>" in (updated.meta or {}).get("description", "")

    def test_create_and_update_manifestation_sanitizes_description(self, app: Any) -> None:
        with app.app_context():
            work = create_work(title="Manifestation San Test")
            expr = create_expression(work_id=work.id)
            manif = create_manifestation(
                expression_id=expr.id,
                meta={"description": "Text <script>bad()</script>"},
            )
            assert "<script>" not in (manif.meta or {}).get("description", "")

            updated = update_manifestation(
                manif.id,
                meta={"description": 'Updated <iframe src="x"></iframe><strong>Bold</strong>'},
            )
            assert "<iframe" not in (updated.meta or {}).get("description", "")
            assert "<strong>Bold</strong>" in (updated.meta or {}).get("description", "")

    def test_merge_metadata_sanitizes_description(self) -> None:
        target_meta = {"description": "<script>alert(1)</script><p>Target</p>"}
        source_meta = {"Description": "<object data='x'></object><b>Source</b>"}
        merged = _merge_metadata(target_meta, source_meta)
        assert "<script>" not in merged.get("description", "")
        assert "<object" not in merged.get("Description", "")

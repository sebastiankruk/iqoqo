"""Tests for Section 7 Batch Watermarking Automation CLI (scripts/generate_ai_covers.py)."""

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

from unittest.mock import patch

from app.core.frbr_service import create_expression, create_manifestation, create_work
from scripts.generate_ai_covers import get_unwatermarked_manifestations, load_prompt_spec, process_batch


def test_load_prompt_spec_fallback():
    spec = load_prompt_spec("non_existent_file.md")
    assert "FRBR media cover" in spec


def test_get_unwatermarked_manifestations(app):
    with app.app_context():
        work = create_work("Batch Test Title")
        expr = create_expression(work.id, content_type="movie")
        manif = create_manifestation(expr.id, format="bluray")

        unwatermarked = get_unwatermarked_manifestations()
        assert any(m.id == manif.id for m in unwatermarked)


def test_process_batch_dry_run(app):
    with app.app_context():
        work = create_work("Dry Run Work")
        expr = create_expression(work.id, content_type="book")
        manif = create_manifestation(expr.id, format="hardcover")

        stats = process_batch([manif], dry_run=True)
        assert stats["total"] == 1
        assert stats["skipped"] == 1
        assert stats["processed"] == 0


@patch("scripts.generate_ai_covers.fetch_llm_cover")
def test_process_batch_generation(mock_fetch, app):
    mock_fetch.return_value = ("/static/covers/test_dalle.jpg", "llm_openai")

    with app.app_context():
        work = create_work("AI Generation Test Work")
        expr = create_expression(work.id, content_type="music")
        manif = create_manifestation(expr.id, format="vinyl")

        stats = process_batch([manif], dry_run=False)
        assert stats["generated"] == 1
        assert stats["processed"] == 1
        assert manif.cover_url == "/static/covers/test_dalle.jpg"

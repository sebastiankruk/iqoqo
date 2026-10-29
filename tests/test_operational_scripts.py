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
"""Operational tests for administrative CLI scripts: archive_orphans, generate_ai_covers, init_geonames_db."""

import io
import os
import sqlite3
import zipfile
from unittest.mock import MagicMock, patch

import pytest

from app.db.models import Expression, Manifestation, Work, db
from scripts.archive_orphans import schedule_missing_covers
from scripts.generate_ai_covers import (
    get_unwatermarked_manifestations,
    load_prompt_spec,
    process_batch,
)
from scripts.init_geonames_db import build_database, download_dump

# ---------------------------------------------------------------------------
# scripts/archive_orphans.py
# ---------------------------------------------------------------------------


def test_schedule_missing_covers_invokes_pipeline(app):
    """schedule_missing_covers invokes process_cover_pipeline for manifestations without covers."""
    with app.app_context():
        work = Work(title="Missing Cover Book", meta={"authors": ["Author Person"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(expression_id=expr.id, isbn13="9780000000001", cover_url=None)
        db.session.add(manif)
        db.session.commit()
        manif_id = manif.id

    with patch("app.utils.covers.process_cover_pipeline") as mock_pipeline:
        schedule_missing_covers(app=app)
        assert mock_pipeline.called
        args, kwargs = mock_pipeline.call_args
        assert args[0] == manif_id
        assert args[1] == "9780000000001"
        assert args[2] == "Missing Cover Book"


# ---------------------------------------------------------------------------
# scripts/generate_ai_covers.py
# ---------------------------------------------------------------------------


def test_load_prompt_spec_fallback_and_custom(tmp_path):
    """load_prompt_spec returns default fallback or reads custom template."""
    fallback = load_prompt_spec("/nonexistent/prompt.md")
    assert "FRBR media cover" in fallback

    custom_file = tmp_path / "custom_prompt.md"
    custom_file.write_text("Custom prompt for {title} by {author}", encoding="utf-8")
    loaded = load_prompt_spec(str(custom_file))
    assert loaded == "Custom prompt for {title} by {author}"


def test_get_unwatermarked_manifestations_and_batch_dry_run(app):
    """get_unwatermarked_manifestations finds unwatermarked covers and dry-run skips execution."""
    with app.app_context():
        work = Work(title="AI Cover Test", meta={})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(
            expression_id=expr.id,
            cover_url=None,
            meta={"failed_llm_attempts": 0},
        )
        db.session.add(manif)
        db.session.commit()

        unwatermarked = get_unwatermarked_manifestations(limit=10)
        assert any(m.id == manif.id for m in unwatermarked)

        stats = process_batch([manif], dry_run=True)
        assert stats["total"] == 1
        assert stats["skipped"] == 1
        assert stats["generated"] == 0


def test_process_batch_circuit_breaker(app):
    """process_batch respects the circuit breaker and skips items with >=3 failed attempts."""
    with app.app_context():
        work = Work(title="Circuit Breaker Test", meta={})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(
            expression_id=expr.id,
            cover_url=None,
            meta={"failed_llm_attempts": 3},
        )
        db.session.add(manif)
        db.session.commit()

        # Without force_retry, should be skipped
        stats = process_batch([manif], dry_run=False, force_retry=False)
        assert stats["skipped"] == 1
        assert stats["generated"] == 0


# ---------------------------------------------------------------------------
# scripts/init_geonames_db.py
# ---------------------------------------------------------------------------


def test_download_dump_guards_untrusted_urls():
    """download_dump rejects non-HTTPS and non-GeoNames URLs."""
    with pytest.raises(ValueError, match="Untrusted download URL"):
        download_dump("http://download.geonames.org/export/dump/cities15000.zip")

    with pytest.raises(ValueError, match="Untrusted download URL"):
        download_dump("https://evil.com/dump.zip")


def test_build_database_populates_sqlite_schema(tmp_path):
    """build_database creates cities and alt_names tables from zip content."""
    # Build fake in-memory cities15000.zip
    cities_tsv = (
        "3041563\tAndorra la Vella\tAndorra la Vella\tAndorra,Andorre\t42.50779\t1.52109\tP\tPPLC\tAD\t\t07\t\t\t20430\t1029\tEurope/Andorra\t2023-01-01\n"
        "2988507\tParis\tParis\tVille de Paris,Lutèce\t48.85341\t2.3488\tP\tPPLC\tFR\t\t11\t75\t75056\t2138551\t35\tEurope/Paris\t2023-01-01\n"
    )

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("cities15000.txt", cities_tsv.encode("utf-8"))
    zip_bytes = zip_buffer.getvalue()

    target_db = tmp_path / "test_cities.db"
    inserted = build_database(zip_bytes, str(target_db))
    assert inserted == 2
    assert target_db.exists()

    conn = sqlite3.connect(str(target_db))
    cursor = conn.cursor()
    cursor.execute("SELECT name, country_code, population FROM cities ORDER BY geoname_id ASC")
    rows = cursor.fetchall()
    assert len(rows) == 2
    assert rows[0][0] == "Paris"
    assert rows[1][0] == "Andorra la Vella"

    # Verify alt_names table populated
    cursor.execute("SELECT name_lower FROM alt_names WHERE geoname_id = 2988507")
    alt_names = {r[0] for r in cursor.fetchall()}
    assert "paris" in alt_names
    assert "lutèce" in alt_names
    conn.close()

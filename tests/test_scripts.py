"""Tests for operational scripts (backup, restore, archive)."""

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

import json
import os
import shutil
import zipfile
from unittest.mock import MagicMock, patch

import pytest

from app.config import Config
from app.db import db
from app.db.models import Expression, Manifestation, Work

# Import scripts (using sys.path hack in scripts requires us to be careful with imports in tests)
from scripts.archive_orphans import archive_orphaned_covers, schedule_missing_covers
from scripts.backup import create_export
from scripts.fetch_covers import run_batch
from scripts.restore_covers import restore_covers


def test_archive_orphaned_covers(app, tmp_path):
    """Test that orphaned files are moved to archive."""
    archive_dir = tmp_path / "archive"
    covers_dir = tmp_path / "covers"
    covers_dir.mkdir(parents=True, exist_ok=True)
    (covers_dir / "keep.jpg").touch()
    (covers_dir / "orphan.jpg").touch()

    with (
        patch("scripts.archive_orphans.COVERS_DIR", str(covers_dir)),
        patch.dict(os.environ, {"COVERS_ARCHIVE_DIR": str(archive_dir)}),
        patch("app.db.models.Manifestation.query") as mock_query,
    ):
        mock_manif = MagicMock()
        mock_manif.cover_url = "/static/covers/keep.jpg"
        mock_query.filter.return_value.all.return_value = [mock_manif]

        archive_orphaned_covers(app=app)

        assert (covers_dir / "keep.jpg").exists()
        assert not (covers_dir / "orphan.jpg").exists()
        assert (archive_dir / "orphan.jpg").exists()


def test_schedule_missing_covers_null_path(app, tmp_path):
    """Manifestations with cover_url=None are passed to the pipeline."""
    mock_manif = MagicMock()
    mock_manif.id = 42
    mock_manif.isbn13 = "9780000000000"
    mock_manif.cover_url = None
    mock_manif.expression.work.title = "Test Book"
    mock_manif.expression.work.meta = {"authors": ["Test Author"]}

    with (
        patch("app.db.models.Manifestation.query") as mock_query,
        patch("app.utils.covers.process_cover_pipeline") as mock_pipeline,
    ):
        mock_query.all.return_value = [mock_manif]

        schedule_missing_covers(app=app)

        mock_pipeline.assert_called_once_with(42, "9780000000000", "Test Book", "Test Author")


def test_schedule_missing_covers_file_absent(app, tmp_path):
    """Manifestations whose cover file is missing on disk are scheduled."""
    mock_manif = MagicMock()
    mock_manif.id = 7
    mock_manif.isbn13 = "9780000000001"
    mock_manif.cover_url = "/static/covers/gone.jpg"
    mock_manif.expression.work.title = "Gone Book"
    mock_manif.expression.work.meta = {"authors": ["Some Author"]}

    with (
        patch("app.config.Config.BASE_DIR", str(tmp_path)),
        patch("app.db.models.Manifestation.query") as mock_query,
        patch("app.utils.covers.process_cover_pipeline") as mock_pipeline,
    ):
        mock_query.all.return_value = [mock_manif]
        # File deliberately NOT created → pipeline should be called
        schedule_missing_covers(app=app)
        mock_pipeline.assert_called_once_with(7, "9780000000001", "Gone Book", "Some Author")


def test_backup_creation(app, tmp_path):
    """Test that backup creates a zip file with metadata and covers."""
    # Create dummy covers dir in temp path
    covers_dir = tmp_path / "app" / "static" / "covers"
    covers_dir.mkdir(parents=True, exist_ok=True)

    with (
        patch.dict(os.environ, {"BACKUP_DIR": str(tmp_path)}),
        patch("app.config.Config.BASE_DIR", str(tmp_path)),
        patch("app.core.data_manager.DataManager.export_all") as mock_export,
    ):

        mock_export.return_value = {"test": "data"}

        create_export(app=app)

        # Check if zip exists
        zips = list(tmp_path.glob("*.zip"))
        assert len(zips) == 1

        with zipfile.ZipFile(zips[0], "r") as z:
            assert "metadata.json" in z.namelist()


def test_restore_covers(app, tmp_path):
    """Test restoring covers from a zip."""
    # Create a dummy backup zip
    backup_zip = tmp_path / "backup.zip"
    with zipfile.ZipFile(backup_zip, "w") as z:
        z.writestr("metadata.json", json.dumps({"manifestations": [{"isbn13": "123", "cover_url": "/c.jpg"}]}))
        z.writestr("covers/c.jpg", b"image data")

    with patch("app.config.Config.BASE_DIR", str(tmp_path)):

        # Create target dir
        (tmp_path / "app" / "static" / "covers").mkdir(parents=True, exist_ok=True)

        restore_covers(str(backup_zip), app=app)

        assert (tmp_path / "app" / "static" / "covers" / "c.jpg").exists()


def test_fetch_covers_run_batch(app):
    """Test fetch_covers.run_batch query logic with real DB (SQLite)."""
    with app.app_context():
        # Create parent objects to satisfy foreign key constraints
        work = Work(title="Test Work", meta={})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text", language="en", meta={})
        db.session.add(expr)
        db.session.flush()

        # 1. No cover, no meta (should process)
        m1 = Manifestation(expression_id=expr.id, isbn13="9781000000001", meta={})
        # 2. No cover, failed status (should skip unless force)
        m2 = Manifestation(expression_id=expr.id, isbn13="9781000000002", meta={"cover_status": "failed"})
        # 3. No cover, other status (should process)
        m3 = Manifestation(expression_id=expr.id, isbn13="9781000000003", meta={"cover_status": "pending"})
        # 4. Has cover (should skip)
        m4 = Manifestation(expression_id=expr.id, isbn13="9781000000004", cover_url="/covers/exist.jpg", meta={})

        db.session.add_all([m1, m2, m3, m4])
        db.session.commit()

        m1_id, m2_id, m3_id = m1.id, m2.id, m3.id

    # Patch the pipeline to avoid actual work and sleep to speed up
    with (
        patch("scripts.fetch_covers.process_cover_pipeline") as mock_pipeline,
        patch("scripts.fetch_covers.time.sleep"),
    ):
        # Run normal batch
        run_batch(app=app)

        assert mock_pipeline.call_count == 2
        processed_ids = {call.args[0] for call in mock_pipeline.call_args_list}
        assert m1_id in processed_ids
        assert m3_id in processed_ids
        assert m2_id not in processed_ids

        # Run force batch
        mock_pipeline.reset_mock()
        run_batch(force=True, app=app)

        # Should process m1, m2, m3 (m4 still has cover)
        assert mock_pipeline.call_count == 3
        processed_ids = {call.args[0] for call in mock_pipeline.call_args_list}
        assert m2_id in processed_ids

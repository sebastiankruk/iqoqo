"""Tests for operational scripts (backup, restore, archive)."""

import json
import os
import shutil
import zipfile
from unittest.mock import MagicMock, patch

import pytest

from app.config import Config
from app.db.models import Manifestation

# Import scripts (using sys.path hack in scripts requires us to be careful with imports in tests)
from scripts.archive_orphans import archive_orphaned_covers, schedule_missing_covers
from scripts.backup import create_export
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
        patch("scripts.archive_orphans.app", app),
    ):
        mock_manif = MagicMock()
        mock_manif.cover_path = "/static/covers/keep.jpg"
        mock_query.filter.return_value.all.return_value = [mock_manif]

        archive_orphaned_covers()

        assert (covers_dir / "keep.jpg").exists()
        assert not (covers_dir / "orphan.jpg").exists()
        assert (archive_dir / "orphan.jpg").exists()


def test_schedule_missing_covers_null_path(app, tmp_path):
    """Manifestations with cover_path=None are passed to the pipeline."""
    mock_manif = MagicMock()
    mock_manif.id = 42
    mock_manif.isbn13 = "9780000000000"
    mock_manif.cover_path = None
    mock_manif.expression.work.title = "Test Book"
    mock_manif.expression.work.meta = {"authors": ["Test Author"]}

    with (
        patch("scripts.archive_orphans.app", app),
        patch("app.db.models.Manifestation.query") as mock_query,
        patch("app.utils.covers.process_cover_pipeline") as mock_pipeline,
    ):
        mock_query.all.return_value = [mock_manif]

        schedule_missing_covers()

        mock_pipeline.assert_called_once_with(42, "9780000000000", "Test Book", "Test Author")


def test_schedule_missing_covers_file_absent(app, tmp_path):
    """Manifestations whose cover file is missing on disk are scheduled."""
    mock_manif = MagicMock()
    mock_manif.id = 7
    mock_manif.isbn13 = "9780000000001"
    mock_manif.cover_path = "/static/covers/gone.jpg"
    mock_manif.expression.work.title = "Gone Book"
    mock_manif.expression.work.meta = {"authors": ["Some Author"]}

    with (
        patch("scripts.archive_orphans.app", app),
        patch("app.config.Config.BASE_DIR", str(tmp_path)),
        patch("app.db.models.Manifestation.query") as mock_query,
        patch("app.utils.covers.process_cover_pipeline") as mock_pipeline,
    ):
        mock_query.all.return_value = [mock_manif]
        # File deliberately NOT created → pipeline should be called
        schedule_missing_covers()
        mock_pipeline.assert_called_once_with(7, "9780000000001", "Gone Book", "Some Author")


def test_backup_creation(app, tmp_path):
    """Test that backup creates a zip file with metadata and covers."""
    with (
        patch("scripts.backup.app", app),
        patch.dict(os.environ, {"BACKUP_DIR": str(tmp_path)}),
        patch("app.core.data_manager.DataManager.export_all") as mock_export,
    ):

        mock_export.return_value = {"test": "data"}

        # Create dummy covers dir
        covers_dir = os.path.join(Config.BASE_DIR, "app", "static", "covers")
        os.makedirs(covers_dir, exist_ok=True)

        create_export()

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
        z.writestr("metadata.json", json.dumps({"manifestations": [{"isbn13": "123", "cover_path": "/c.jpg"}]}))
        z.writestr("covers/c.jpg", b"image data")

    with patch("scripts.restore_covers.app", app), patch("app.config.Config.BASE_DIR", str(tmp_path)):

        # Create target dir
        (tmp_path / "app" / "static" / "covers").mkdir(parents=True, exist_ok=True)

        restore_covers(str(backup_zip))

        assert (tmp_path / "app" / "static" / "covers" / "c.jpg").exists()

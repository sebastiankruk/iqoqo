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
from scripts.archive_orphans import archive_orphaned_covers
from scripts.backup import create_export
from scripts.restore_covers import restore_covers


def test_archive_orphaned_covers(app, tmp_path):
    """Test that orphaned files are moved to archive."""
    # Setup directories
    covers_dir = tmp_path / "covers"
    archive_dir = tmp_path / "archive"
    covers_dir.mkdir()

    # Create dummy files
    (covers_dir / "keep.jpg").touch()
    (covers_dir / "orphan.jpg").touch()

    # Mock Config and DB
    with patch("app.config.Config.BASE_DIR", str(tmp_path)), \
         patch.dict(os.environ, {"COVERS_ARCHIVE_DIR": str(archive_dir)}), \
         patch("app.db.models.Manifestation.query") as mock_query:

        # Mock DB returning one valid cover
        mock_manif = MagicMock()
        mock_manif.cover_path = "/static/covers/keep.jpg"
        mock_query.filter.return_value.all.return_value = [mock_manif]

        # Run script logic (we mock the app context inside the script via the app object imported there)
        # But since we import the function, we need to mock the app object used inside the script
        with patch("scripts.archive_orphans.app", app):
            # We also need to patch the hardcoded paths inside the function if they don't use the mocked Config correctly
            # The script uses Config.BASE_DIR, which we patched.
            # However, the script constructs paths relative to "app/static/covers".
            # Let's mock the paths directly for easier testing.
            with patch("scripts.archive_orphans.os.path.join") as mock_join:
                # Complex mocking of join is fragile, let's rely on the Config patch
                # and ensure the directory structure matches what the script expects:
                # Config.BASE_DIR / "app" / "static" / "covers"
                real_structure = tmp_path / "app" / "static" / "covers"
                real_structure.mkdir(parents=True, exist_ok=True)
                (real_structure / "keep.jpg").touch()
                (real_structure / "orphan.jpg").touch()

                archive_orphaned_covers()

                assert (real_structure / "keep.jpg").exists()
                assert not (real_structure / "orphan.jpg").exists()
                assert (archive_dir / "orphan.jpg").exists()

def test_backup_creation(app, tmp_path):
    """Test that backup creates a zip file with metadata and covers."""
    with patch("scripts.backup.app", app), \
         patch.dict(os.environ, {"BACKUP_DIR": str(tmp_path)}), \
         patch("app.core.data_manager.DataManager.export_all") as mock_export:

        mock_export.return_value = {"test": "data"}

        # Create dummy covers dir
        covers_dir = os.path.join(Config.BASE_DIR, "app", "static", "covers")
        os.makedirs(covers_dir, exist_ok=True)

        create_export()

        # Check if zip exists
        zips = list(tmp_path.glob("*.zip"))
        assert len(zips) == 1

        with zipfile.ZipFile(zips[0], 'r') as z:
            assert "metadata.json" in z.namelist()

def test_restore_covers(app, tmp_path):
    """Test restoring covers from a zip."""
    # Create a dummy backup zip
    backup_zip = tmp_path / "backup.zip"
    with zipfile.ZipFile(backup_zip, 'w') as z:
        z.writestr("metadata.json", json.dumps({"manifestations": [{"isbn13": "123", "cover_path": "/c.jpg"}]}))
        z.writestr("covers/c.jpg", b"image data")

    with patch("scripts.restore_covers.app", app), \
         patch("app.config.Config.BASE_DIR", str(tmp_path)):

        # Create target dir
        (tmp_path / "app" / "static" / "covers").mkdir(parents=True, exist_ok=True)

        restore_covers(str(backup_zip))

        assert (tmp_path / "app" / "static" / "covers" / "c.jpg").exists()        restore_covers(str(backup_zip))

        assert (tmp_path / "app" / "static" / "covers" / "c.jpg").exists()        restore_covers(str(backup_zip))

        assert (tmp_path / "app" / "static" / "covers" / "c.jpg").exists()

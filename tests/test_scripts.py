"""Tests for operational scripts (restore, archive)."""

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
import subprocess
import zipfile
from unittest.mock import MagicMock, patch

import pytest

from app.config import Config
from app.db import db
from app.db.models import Expression, Manifestation, Work

# Import scripts (using sys.path hack in scripts requires us to be careful with imports in tests)
from scripts.archive_orphans import archive_orphaned_covers, schedule_missing_covers
from scripts.backfill_legacy_covers import DatabaseConnectivityError, database_target, run_backfill
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

        mock_pipeline.assert_called_once_with(
            42,
            "9780000000000",
            "Test Book",
            "Test Author",
            llm_permissions={"allow_generate_cover": True, "allow_cloud_llm": True},
        )


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
        mock_pipeline.assert_called_once_with(
            7,
            "9780000000001",
            "Gone Book",
            "Some Author",
            llm_permissions={"allow_generate_cover": True, "allow_cloud_llm": True},
        )


def test_legacy_cover_backfill_dry_run_selects_only_allowlisted_sources(app, capsys):
    """Dry-run selects legacy column/meta sources but does not mutate or process them."""
    with app.app_context():
        work = Work(title="Legacy Cover Book", meta={"authors": ["Test Author"]})
        db.session.add(work)
        db.session.flush()
        expression = Expression(work_id=work.id, content_type="text", meta={})
        db.session.add(expression)
        db.session.flush()

        column_source = Manifestation(
            expression_id=expression.id,
            cover_url="https://i.discogs.com/covers/column.jpg?X-Amz-Signature=column-secret",
            meta={},
        )
        meta_source = Manifestation(
            expression_id=expression.id,
            cover_url=None,
            meta={"cover_url": "HTTPS://a.allegroimg.com/original/meta.jpg?token=meta-secret"},
        )
        unsupported = Manifestation(
            expression_id=expression.id,
            cover_url="https://unknown.example/cover.jpg?signature=unknown-secret",
            meta={},
        )
        already_local = Manifestation(
            expression_id=expression.id,
            cover_url="/static/covers/already-local.jpg",
            meta={
                "cover_url": "https://i.discogs.com/covers/already-local-source.jpg",
                "cover_status": "ready",
            },
        )
        db.session.add_all([column_source, meta_source, unsupported, already_local])
        db.session.commit()
        original_ids = {m.id for m in (column_source, meta_source, unsupported, already_local)}
        original_url_values = {
            column_source.id: column_source.cover_url,
            meta_source.id: meta_source.cover_url,
            unsupported.id: unsupported.cover_url,
            already_local.id: already_local.cover_url,
        }
        original_meta_values = {
            column_source.id: dict(column_source.meta),
            meta_source.id: dict(meta_source.meta),
            unsupported.id: dict(unsupported.meta),
            already_local.id: dict(already_local.meta),
        }

    with patch("scripts.backfill_legacy_covers.process_cover_pipeline") as pipeline:
        counts = run_backfill(app=app)

    output = capsys.readouterr().out
    assert counts == {
        "candidates": 4,
        "eligible": 2,
        "already_local_ready": 1,
        "unsupported_host": 1,
        "processed": 0,
        "failed": 0,
    }
    pipeline.assert_not_called()
    assert "column-secret" not in output
    assert "meta-secret" not in output
    assert "unknown-secret" not in output

    with app.app_context():
        persisted = {m.id: m for m in Manifestation.query.filter(Manifestation.id.in_(original_ids)).all()}
        for manifestation_id, cover_url in original_url_values.items():
            assert persisted[manifestation_id].cover_url == cover_url
            assert persisted[manifestation_id].meta == original_meta_values[manifestation_id]


def test_legacy_cover_backfill_apply_requires_target_and_is_idempotent(app):
    """Apply processes only allowlisted inputs and skips completed copies on rerun."""
    with app.app_context():
        work = Work(title="Backfill Target", meta={"authors": ["Test Author"]})
        db.session.add(work)
        db.session.flush()
        expression = Expression(work_id=work.id, content_type="text", meta={})
        db.session.add(expression)
        db.session.flush()
        source = Manifestation(
            expression_id=expression.id,
            cover_url=None,
            meta={"cover_url": "https://i.discogs.com/covers/backfill.jpg?X-Amz-Signature=private-value"},
        )
        unsupported = Manifestation(
            expression_id=expression.id,
            cover_url="https://attacker.example/cover.jpg",
            meta={},
        )
        db.session.add_all([source, unsupported])
        db.session.commit()
        source_id = source.id
        unsupported_id = unsupported.id
        target = database_target(db.engine.url)

    with (
        patch("scripts.backfill_legacy_covers.process_cover_pipeline") as pipeline,
        pytest.raises(ValueError, match="confirm-target"),
    ):
        run_backfill(app=app, apply=True, confirm_target="wrong-target")
    pipeline.assert_not_called()

    def complete_cover(manifestation_id, *_args, legacy_source_only=False, **_kwargs):
        assert legacy_source_only is True
        manifestation = db.session.get(Manifestation, manifestation_id)
        manifestation.cover_url = f"/static/covers/backfill-{manifestation_id}.jpg"
        manifestation.update_meta(cover_status="ready", cover_source="api_direct_download")
        db.session.commit()

    with patch("scripts.backfill_legacy_covers.process_cover_pipeline", side_effect=complete_cover) as pipeline:
        applied = run_backfill(app=app, apply=True, confirm_target=target)

    assert applied["candidates"] == 2
    assert applied["eligible"] == 1
    assert applied["unsupported_host"] == 1
    assert applied["processed"] == 1
    assert applied["failed"] == 0
    pipeline.assert_called_once()
    assert pipeline.call_args.args[0] == source_id
    assert pipeline.call_args.kwargs["legacy_source_only"] is True
    assert pipeline.call_args.kwargs["llm_permissions"] == {"allow_generate_cover": False, "allow_cloud_llm": False}

    with patch("scripts.backfill_legacy_covers.process_cover_pipeline") as pipeline:
        rerun = run_backfill(app=app, apply=True, confirm_target=target)

    assert rerun["already_local_ready"] == 1
    assert rerun["eligible"] == 0
    assert rerun["processed"] == 0
    pipeline.assert_not_called()

    with app.app_context():
        assert db.session.get(Manifestation, source_id).cover_url == f"/static/covers/backfill-{source_id}.jpg"
        assert db.session.get(Manifestation, unsupported_id).cover_url == "https://attacker.example/cover.jpg"


def test_database_target_redacts_credentials_and_query_values():
    """The operator confirmation identity must not expose database secrets."""
    from sqlalchemy.engine import make_url

    target = database_target(make_url("postgresql://db-user:db-password@preview-clone.internal:5432/iqoqo?token=db-token"))

    assert target == "postgresql://preview-clone.internal:5432/iqoqo"
    assert "db-password" not in target
    assert "db-token" not in target


def test_legacy_cover_backfill_stops_before_scanning_when_database_is_unreachable(app):
    """A bad container DB hostname fails before candidate queries or processing."""
    from sqlalchemy.exc import OperationalError

    with (
        patch(
            "scripts.backfill_legacy_covers.db.session.execute",
            side_effect=OperationalError("SELECT 1", {}, OSError("connection refused")),
        ),
        patch("scripts.backfill_legacy_covers._iter_candidates") as candidates,
        pytest.raises(DatabaseConnectivityError, match="configured database target"),
    ):
        run_backfill(app=app)

    candidates.assert_not_called()


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


def test_clone_script_argument_validation(tmp_path):
    """Test that scripts/clone.sh validates arguments properly."""
    # Ensure clone.sh path is correct
    clone_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "clone.sh")

    # Run with no arguments (should fail with usage)
    res = subprocess.run([clone_script], capture_output=True, text=True, check=False)
    assert res.returncode != 0
    assert "Usage:" in res.stdout or "Usage:" in res.stderr

    # Run with too many arguments (should fail with usage)
    res = subprocess.run(
        [clone_script, "/nonexistent1", "prod", "/nonexistent2", "preview", "host", "extra"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode != 0
    assert "Usage:" in res.stdout or "Usage:" in res.stderr

    # Run with correct number of arguments but non-existent dirs (local)
    res = subprocess.run(
        [clone_script, "/nonexistent1", "prod", "/nonexistent2", "preview"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode != 0
    assert "Error: Source directory" in res.stdout or "Error: Source directory" in res.stderr

    # Run with remote host and non-existent/unreachable host (should fail)
    res = subprocess.run(
        [clone_script, "/nonexistent1", "prod", "/nonexistent2", "preview", "nonexistent-host-xyz"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode != 0
    assert "Error: Remote source directory" in res.stdout or "Error: Remote source directory" in res.stderr

    # Create temporary source and destination directories but no env files (local)
    src_dir = tmp_path / "src"
    dst_dir = tmp_path / "dst"
    src_dir.mkdir()
    dst_dir.mkdir()

    res = subprocess.run(
        [clone_script, str(src_dir), "prod", str(dst_dir), "preview"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode != 0
    assert "Error: Source env file" in res.stdout or "Error: Source env file" in res.stderr

    # Create source env file but no destination env file (local)
    (src_dir / ".env.prod").touch()
    res = subprocess.run(
        [clone_script, str(src_dir), "prod", str(dst_dir), "preview"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode != 0
    assert "Error: Destination env file" in res.stdout or "Error: Destination env file" in res.stderr


def test_backfill_work_genres_script(app):
    """Test backfilling genres from Manifestation meta into Work meta."""
    from scripts.migrations.backfill_work_genres import backfill_work_genres

    with app.app_context():
        work = Work(title="Sci-Fi Epic", meta={})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text", language="en", meta={})
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(
            expression_id=expr.id,
            meta={"Categories": ["Science Fiction", "Space Opera"]},
        )
        db.session.add(manif)
        db.session.commit()

        work_id = work.id

        stats = backfill_work_genres(batch_size=10, app=app)
        assert stats["updated_works"] == 1

        db.session.expire_all()
        updated_work = db.session.get(Work, work_id)
        assert updated_work.meta.get("genres") == ["Science Fiction", "Space Opera"]


def test_fix_invalid_item_statuses_script(app):
    """Test repairing invalid item statuses via standalone script."""
    from app.db.models import Item, User
    from scripts.migrations.fix_invalid_item_statuses import fix_invalid_item_statuses

    with app.app_context():
        user = User(email="status_fixer@example.com")
        user.set_password("test-password")
        db.session.add(user)
        db.session.flush()

        work = Work(title="Status Test Work", meta={})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="movie", language="en", meta={})
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(expression_id=expr.id, meta={})
        db.session.add(manif)
        db.session.flush()

        # Item with legacy 'unread' status on a movie
        item = Item(
            manifestation_id=manif.id,
            owner_id=user.id,
            status="unread",
            collection_status="available",
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

        stats = fix_invalid_item_statuses(batch_size=10, app=app)
        assert stats["updated_items"] == 1

        db.session.expire_all()
        repaired_item = db.session.get(Item, item_id)
        assert repaired_item.status == "want_to_watch"


def test_migrate_wishlist_intents_script(app):
    """Test migrating legacy wishlist items to UserWorkIntent via standalone script."""
    from app.db.models import Item, User, UserWorkIntent
    from scripts.migrations.migrate_wishlist_intents import migrate_wishlist_intents

    with app.app_context():
        user = User(email="wishlist_tester@example.com")
        user.set_password("test-password")
        db.session.add(user)
        db.session.flush()

        work = Work(title="Wishlist Work", meta={})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text", language="en", meta={})
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(expression_id=expr.id, meta={})
        db.session.add(manif)
        db.session.flush()

        # Item with legacy 'wish_list' collection status
        item = Item(
            manifestation_id=manif.id,
            owner_id=user.id,
            status="want_to_read",
            collection_status="wish_list",
        )
        db.session.add(item)
        db.session.commit()

        user_id = user.id
        work_id = work.id
        item_id = item.id

        stats = migrate_wishlist_intents(batch_size=10, app=app)
        assert stats["created_intents"] == 1
        assert stats["deleted_legacy_items"] == 1

        db.session.expire_all()
        # Check intent created
        intent = db.session.execute(
            db.select(UserWorkIntent).where(
                UserWorkIntent.user_id == user_id,
                UserWorkIntent.work_id == work_id,
            )
        ).scalar_one_or_none()
        assert intent is not None
        assert intent.status == "want_to_read"

        # Check item deleted
        assert db.session.get(Item, item_id) is None

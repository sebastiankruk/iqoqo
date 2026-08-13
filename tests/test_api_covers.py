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
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def setup_celery_eager(app):
    """Ensure Celery runs tasks synchronously for tests."""
    from app.core.celery_app import celery

    celery.conf.broker_url = "memory://"
    celery.conf.result_backend = "cache+memory://"
    celery.conf.task_always_eager = True
    celery.conf.task_store_eager_result = True
    yield
    celery.conf.task_always_eager = False
    celery.conf.task_store_eager_result = False


def test_regenerate_cover_returns_task_id(client, admin_headers):
    from app.db.models import Expression, Manifestation, Work, db

    with client.application.app_context():
        work = Work(title="Regen Test", meta={"authors": ["Author Regen"]})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, isbn13="2222222222222")
        db.session.add(manif)
        db.session.commit()
        manif_id = manif.id

    with patch("app.api.manifestations.start_cover_processing", return_value="fake-task-id"):
        response = client.post(f"/api/manifestations/{manif_id}/regenerate-cover", headers=admin_headers)
        assert response.status_code == 202
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["task_id"] == "fake-task-id"


def test_regenerate_cover_empty_authors(client, admin_headers):
    """Verify that regenerating a cover does not crash with IndexError when authors list is empty."""
    from app.db.models import Expression, Manifestation, Work, db

    with client.application.app_context():
        work = Work(title="Regen Empty Authors", meta={"authors": []})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, isbn13="3333333333333")
        db.session.add(manif)
        db.session.commit()
        manif_id = manif.id

    with patch("app.api.manifestations.start_cover_processing", return_value="fake-task-id"):
        response = client.post(f"/api/manifestations/{manif_id}/regenerate-cover", headers=admin_headers)
        assert response.status_code == 202

        # Test refetch cover too
        response_refetch = client.post(f"/api/manifestations/{manif_id}/refetch-cover", headers=admin_headers)
        assert response_refetch.status_code == 202


def test_get_cover_status_polling(client, normal_user_headers):
    from app.db.models import Expression, Manifestation, Work, db

    with client.application.app_context():
        work = Work(title="Status Test")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, isbn13="3333333333333", cover_url="/static/covers/old.jpg")
        db.session.add(manif)
        db.session.commit()
        manif_id = manif.id

    # Test 1: Fallback (no task_id)
    response = client.get(f"/api/manifestations/{manif_id}/cover-status", headers=normal_user_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["data"]["cover_url"] == "/static/covers/old.jpg"

    # Test 2: With task_id PENDING
    with patch("app.core.tasks.get_task_result", return_value={"status": "pending"}):
        response = client.get(f"/api/manifestations/{manif_id}/cover-status?task_id=t1", headers=normal_user_headers)
        assert response.status_code == 202
        assert response.get_json()["data"]["status"] == "pending"

    # Test 3: With task_id COMPLETED
    with patch("app.core.tasks.get_task_result", return_value={"status": "completed"}):
        response = client.get(f"/api/manifestations/{manif_id}/cover-status?task_id=t2", headers=normal_user_headers)
        assert response.status_code == 200
        assert response.get_json()["data"]["status"] == "ready"

    # Test 4: With task_id FAILED
    with patch("app.core.tasks.get_task_result", return_value={"status": "failed", "error": "Something went wrong"}):
        response = client.get(f"/api/manifestations/{manif_id}/cover-status?task_id=t3", headers=normal_user_headers)
        assert response.status_code == 200
        assert response.get_json()["success"] is False
        assert response.get_json()["data"]["status"] == "failed"
        assert response.get_json()["error"] == "Something went wrong"


# --- Phase 4: Bug B6-deep — UPC/EAN cover resolution ---


def test_cover_lookup_musicbrainz_upc(app):
    """B6-deep: UPC barcode should resolve cover via MusicBrainz Cover Art Archive."""
    from app.utils.covers import fetch_upc_cover

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"releases": [{"id": "abc-123", "title": "Test Album"}]}

    with patch("app.utils.covers.download_direct_url") as mock_download:
        mock_download.return_value = ("/static/covers/0602445564354_mb.jpg", "api_musicbrainz")
        with patch("app.utils.covers.requests.get", return_value=mock_response):
            result = fetch_upc_cover("0602445564354", content_type="music")

    assert result is not None
    _filename, source = result
    assert "musicbrainz" in source


def test_cover_lookup_tmdb_upc(app):
    """B6-deep: UPC barcode for video should resolve cover via TMDb poster."""
    from app.utils.covers import fetch_upc_cover

    with patch("app.utils.tmdb.fetch_video_metadata") as mock_tmdb:
        mock_tmdb.return_value = {
            "title": "Test Movie",
            "cover_url": "https://image.tmdb.org/t/p/w500/test.jpg",
        }
        with patch("app.utils.covers.download_direct_url") as mock_download:
            mock_download.return_value = ("/static/covers/5051892002196_tmdb.jpg", "api_tmdb")
            result = fetch_upc_cover("5051892002196", content_type="movie")

    assert result is not None
    _filename, source = result
    assert "tmdb" in source


def test_cover_lookup_igdb_upc(app):
    """B6-deep: UPC barcode for game should resolve cover via IGDB poster."""
    from app.utils.covers import fetch_upc_cover

    with patch("app.utils.igdb.fetch_game_metadata") as mock_igdb:
        mock_igdb.return_value = {
            "title": "Test Game",
            "cover_url": "https://images.igdb.com/igdb/image/upload/t_cover_big/test.jpg",
        }
        with patch("app.utils.covers.download_direct_url") as mock_download:
            mock_download.return_value = ("/static/covers/1234567890_igdb.jpg", "api_igdb")
            result = fetch_upc_cover("1234567890", content_type="game")

    assert result is not None
    _filename, source = result
    assert "igdb" in source


def test_cover_lookup_non_isbn_fallback(app):
    """B6-deep: Non-ISBN with no provider match returns None gracefully."""
    from app.utils.covers import fetch_upc_cover

    result = fetch_upc_cover("9999999999999", content_type="text")
    assert result is None


def test_refetch_cover_returns_task_id(client, admin_headers):
    from app.db.models import Expression, Manifestation, Work, db

    with client.application.app_context():
        work = Work(title="Refetch Cover Test", meta={"authors": ["Author Refetch"]})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, isbn13="4444444444444")
        db.session.add(manif)
        db.session.commit()
        manif_id = manif.id

    with patch("app.api.manifestations.start_cover_processing", return_value="fake-refetch-task-id") as mock_start:
        response = client.post(f"/api/manifestations/{manif_id}/refetch-cover", headers=admin_headers)
        assert response.status_code == 202
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["task_id"] == "fake-refetch-task-id"
        mock_start.assert_called_once()
        # Verify LLM permissions are false for refetch
        _, kwargs = mock_start.call_args
        assert kwargs["llm_permissions"] == {"allow_generate_cover": False, "allow_cloud_llm": False}


def test_refetch_cover_falls_back_to_meta_identifier(client, admin_headers):
    from app.db.models import Expression, Manifestation, Work, db

    with client.application.app_context():
        work = Work(title="Refetch Cover Test", meta={"authors": ["Author Refetch"]})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, meta={"barcode": "9781444729764"})
        db.session.add(manif)
        db.session.commit()
        manif_id = manif.id

    with patch("app.api.manifestations.start_cover_processing", return_value="fake-refetch-task-id") as mock_start:
        response = client.post(f"/api/manifestations/{manif_id}/refetch-cover", headers=admin_headers)
        assert response.status_code == 202
        mock_start.assert_called_once()
        args, _ = mock_start.call_args
        assert args[1] == "9781444729764"

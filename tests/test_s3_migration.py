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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Tests for the rclone -> S3Service migration at the call sites (OpenSpec §3.4–§3.5).

The property asserted across every migrated path is that **no subprocess is ever
forked for remote storage**. The old implementation shelled out to ``rclone``
and required a plaintext ``rclone.conf`` bind-mounted into the container; a
regression here would silently reintroduce both.

The backup-archive role (§3.3) had no call site left to test: ``BackupManager``
and ``rotate_and_archive_backups`` were removed as unreachable (no beat-schedule
entry, and ``/data/backups`` was never mounted), so off-site backup archiving is
entirely a host-side concern in ``scripts/cloud_backup.sh``.
"""

import logging
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from app.core.s3_service import (
    BUCKET_COVERS,
    BUCKET_FEEDBACK,
    S3Service,
    S3UploadError,
)


@pytest.fixture(autouse=True)
def _clean_s3_env(monkeypatch):
    """Isolate S3 config so a configured host cannot mask a missing-mock bug."""
    for name in (
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "S3_BUCKET_BACKUP",
        "S3_BUCKET_COVERS",
        "S3_BUCKET_FEEDBACK",
        "RCLONE_COVERS_REMOTE",
        "RCLONE_FEEDBACK_REMOTE",
        "RCLONE_REMOTE_ARCHIVE",
    ):
        monkeypatch.delenv(name, raising=False)
    S3Service.reset_instances()
    yield
    S3Service.reset_instances()


class _RecordingClient:
    """Accepts every write and records it, so tests can assert on the call."""

    def __init__(self) -> None:
        self.uploads: list[tuple] = []
        self.downloads: list[tuple] = []
        self.payload = b"jpeg-bytes"
        self.download_result: str | None = None
        self.get_bytes_error: Exception | None = None
        self.upload_error: Exception | None = None

    def upload_file(self, local_path, bucket, key, ExtraArgs=None):  # noqa: N803  (boto3 casing)
        self.uploads.append((local_path, bucket, key, ExtraArgs))
        if self.upload_error:
            raise self.upload_error

    def download_file(self, bucket, key, local_path):
        self.downloads.append((bucket, key, local_path))
        if self.download_result is None:
            from botocore.exceptions import ClientError  # pylint: disable=import-outside-toplevel

            raise ClientError({"Error": {"Code": "NoSuchKey", "Message": "gone"}}, "GetObject")
        with open(local_path, "wb") as handle:
            handle.write(self.payload)
        return local_path

    def get_object(self, Bucket, Key):  # noqa: N803  (boto3 casing)
        if self.get_bytes_error:
            raise self.get_bytes_error
        body = self.payload
        return {"Body": type("Body", (), {"read": staticmethod(lambda: body)})()}


def _service(role: str) -> S3Service:
    """A real S3Service with a stub client, so key validation still applies."""
    service = S3Service(role, access_key="AKIAEXAMPLE", secret_key="s3cr3t-value")
    service._bucket = f"iqoqo-{role}"  # pylint: disable=protected-access
    service._client = _RecordingClient()  # pylint: disable=protected-access
    return service


def _client(service: S3Service) -> _RecordingClient:
    """The stub client behind a service built by :func:`_service`."""
    return service._client  # pylint: disable=protected-access


@contextmanager
def _patched(module, role: str, service: S3Service | None):
    """Patch ``get_s3_service`` in *module*, since each module imports it by name."""
    with patch.object(module, "get_s3_service", return_value=service):
        yield service


# ── Cover cache (3.4) ────────────────────────────────────────────────────────


def test_cover_save_pushes_to_the_covers_bucket(tmp_path) -> None:
    """A saved cover is pushed to the shared cache via S3, not rclone."""
    from app.utils.images import optimize_and_save_image

    covers = tmp_path / "covers"
    covers.mkdir()
    target = str(covers / "work_1.jpg")
    service = _service(BUCKET_COVERS)

    with (
        patch("app.utils.images.get_s3_service", return_value=service),
        patch("PIL.Image.open", return_value=MagicMock()),
        patch("subprocess.run") as mock_run,
    ):
        optimize_and_save_image(b"fake", target)

    assert not mock_run.called
    uploads = _client(service).uploads
    assert [u[2] for u in uploads] == ["covers/work_1.jpg"]
    assert uploads[0][3] == {"ContentType": "image/jpeg"}


def test_cover_push_failure_is_not_fatal(tmp_path) -> None:
    """A missed cache push must not fail a request the local file already served."""
    from app.utils.images import optimize_and_save_image

    covers = tmp_path / "covers"
    covers.mkdir()
    target = str(covers / "work_1.jpg")
    service = _service(BUCKET_COVERS)
    _client(service).upload_error = S3UploadError("down")

    with patch("app.utils.images.get_s3_service", return_value=service), patch("PIL.Image.open", return_value=MagicMock()):
        optimize_and_save_image(b"fake", target)  # must not raise


def test_cover_save_skips_push_for_non_cover_paths(tmp_path) -> None:
    """Gallery and upload scratch files are not part of the shared cache."""
    from app.utils.images import optimize_and_save_image

    other = tmp_path / "gallery"
    other.mkdir()
    target = str(other / "upload.jpg")
    service = _service(BUCKET_COVERS)

    with patch("app.utils.images.get_s3_service", return_value=service), patch("PIL.Image.open", return_value=MagicMock()):
        optimize_and_save_image(b"fake", target)

    assert _client(service).uploads == []


def test_llm_cover_uses_shared_cache_when_hit(tmp_path) -> None:
    """A cached cover is reused instead of paying for a fresh generation."""
    from app.utils import llm_covers

    service = _service(BUCKET_COVERS)
    _client(service).download_result = "hit"

    with (
        patch.object(llm_covers, "COVERS_DIR", str(tmp_path)),
        patch.object(llm_covers, "get_s3_service", return_value=service),
        patch.object(llm_covers, "generate_cover_local", return_value=None) as local_gen,
    ):
        result = llm_covers.fetch_llm_cover(identifier="work_123", title="T", author="A", user_id="u1")

    assert result[1] == "llm_cache"
    assert not local_gen.called
    # The first suffix tried is 'dalle'; a miss on it is expected.
    assert _client(service).downloads[0][1] == "covers/work_123_dalle.jpg"


def test_llm_cover_falls_through_on_cache_miss(tmp_path) -> None:
    """A miss is routine; generation must proceed normally."""
    from app.utils import llm_covers

    service = _service(BUCKET_COVERS)
    _client(service).download_result = None

    with (
        patch.object(llm_covers, "COVERS_DIR", str(tmp_path)),
        patch.object(llm_covers, "get_s3_service", return_value=service),
        patch.object(llm_covers, "generate_cover_local", return_value=("covers/x.jpg", "local")) as local_gen,
    ):
        result = llm_covers.fetch_llm_cover(identifier="work_123", title="T", author="A", user_id="u1")

    assert result[1] == "local"
    assert local_gen.called
    # All four suffixes are attempted before giving up on the cache.
    assert len(_client(service).downloads) == 4


def test_llm_cover_skips_cache_when_returning_bytes(tmp_path) -> None:
    """Byte-returning callers want fresh output, not a cached file on disk."""
    from app.utils import llm_covers

    service = _service(BUCKET_COVERS)

    with (
        patch.object(llm_covers, "COVERS_DIR", str(tmp_path)),
        patch.object(llm_covers, "get_s3_service", return_value=service),
        patch.object(llm_covers, "generate_cover_local", return_value=(b"bytes", "local")) as local_gen,
    ):
        llm_covers.fetch_llm_cover(identifier="work_123", title="T", author="A", user_id="u1", return_bytes=True)

    assert local_gen.called
    assert _client(service).downloads == []


# ── Feedback screenshots (3.5) ──────────────────────────────────────────────


def test_feedback_upload_uses_s3(tmp_path) -> None:
    """Feedback screenshots are written to the feedback bucket via S3."""
    from app.core.tasks import upload_feedback_screenshot

    local = tmp_path / "shot.jpg"
    local.write_bytes(b"jpeg-bytes")
    service = _service(BUCKET_FEEDBACK)

    with patch("app.core.tasks.get_s3_service", return_value=service), patch("subprocess.run") as mock_run:
        upload_feedback_screenshot(str(local), "shot.jpg")

    assert not mock_run.called
    uploads = _client(service).uploads
    assert [u[2] for u in uploads] == ["feedback/shot.jpg"]
    assert uploads[0][3] == {"ContentType": "image/jpeg"}


def test_feedback_upload_skipped_when_unconfigured(tmp_path, caplog) -> None:
    """No bucket is a normal state for a self-hosted instance, not an error."""
    from app.core.tasks import upload_feedback_screenshot

    local = tmp_path / "shot.jpg"
    local.write_bytes(b"jpeg-bytes")

    with caplog.at_level(logging.INFO), patch("app.core.tasks.get_s3_service", return_value=None):
        upload_feedback_screenshot(str(local), "shot.jpg")

    assert "not configured" in caplog.text


def test_feedback_upload_rejects_traversing_filename(tmp_path) -> None:
    """A filename cannot escape the feedback/ prefix."""
    from app.core.tasks import upload_feedback_screenshot

    local = tmp_path / "shot.jpg"
    local.write_bytes(b"jpeg-bytes")
    service = _service(BUCKET_FEEDBACK)

    with (
        patch("app.core.tasks.get_s3_service", return_value=service),
        pytest.raises(RuntimeError, match="upload failed"),
    ):
        upload_feedback_screenshot(str(local), "../../escape.jpg")

    assert _client(service).uploads == []


def test_feedback_screenshot_fetch_does_not_fork() -> None:
    """The read path uses S3, never a rclone cat subprocess."""
    from app.api import feedback as feedback_api

    service = _service(BUCKET_FEEDBACK)

    with (
        patch.object(feedback_api, "get_s3_service", return_value=service),
        patch("subprocess.run") as mock_run,
    ):
        response = feedback_api._fetch_remote_screenshot("shot.jpg")  # pylint: disable=protected-access

    assert not mock_run.called
    assert response.get_data() == b"jpeg-bytes"


def test_feedback_fetch_reports_404_for_missing_object() -> None:
    """An absent object is a 404, not a 5xx."""
    from botocore.exceptions import ClientError

    from app.api import feedback as feedback_api

    service = _service(BUCKET_FEEDBACK)
    _client(service).get_bytes_error = ClientError({"Error": {"Code": "NoSuchKey", "Message": "gone"}}, "GetObject")

    with patch.object(feedback_api, "get_s3_service", return_value=service):
        _body, status = feedback_api._fetch_remote_screenshot("shot.jpg")  # pylint: disable=protected-access

    assert status == 404


def test_feedback_fetch_reports_502_when_storage_fails() -> None:
    """A permission or outage failure must be distinguishable from a miss."""
    from botocore.exceptions import ClientError

    from app.api import feedback as feedback_api

    service = _service(BUCKET_FEEDBACK)
    _client(service).get_bytes_error = ClientError({"Error": {"Code": "AccessDenied", "Message": "no"}}, "GetObject")

    with patch.object(feedback_api, "get_s3_service", return_value=service):
        _body, status = feedback_api._fetch_remote_screenshot("shot.jpg")  # pylint: disable=protected-access

    assert status == 502


def test_feedback_fetch_rejects_an_unsafe_name_before_any_network_call() -> None:
    """A traversing name is refused by the key guard, not sanitised."""
    from app.api import feedback as feedback_api

    service = _service(BUCKET_FEEDBACK)

    with patch.object(feedback_api, "get_s3_service", return_value=service):
        _body, status = feedback_api._fetch_remote_screenshot("../../escape.jpg")  # pylint: disable=protected-access

    assert status == 400

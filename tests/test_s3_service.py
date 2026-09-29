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

"""Tests for the native S3 object storage service (OpenSpec §3.2–§3.5).

The security properties under test, in priority order:

1. Object keys cannot be steered outside their role prefix by a caller-supplied
   filename. This replaces the ``--`` delimiter that guarded the old rclone
   argument list; without it, a key such as ``../../other-role/x`` would have
   let a cover write into the feedback prefix.
2. Credentials never appear in a log record or an exception message.
3. A missing bucket is reported as unconfigured rather than being silently
   treated as remote storage disabled, and no operation raises in that state.
"""

import logging

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

from app.core.s3_service import (
    BUCKET_BACKUP,
    BUCKET_COVERS,
    BUCKET_FEEDBACK,
    S3ConfigurationError,
    S3DownloadError,
    S3NotConfiguredError,
    S3Service,
    S3UploadError,
    get_s3_service,
    warn_if_legacy_rclone_configured,
)


@pytest.fixture(autouse=True)
def _clean_s3_env(monkeypatch):
    """Isolate every S3 variable so the host environment cannot leak in."""
    for name in (
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_ALLOW_ANONYMOUS",
        "S3_ENDPOINT_URL",
        "S3_REGION_NAME",
        "S3_ADDRESSING_STYLE",
        "S3_BUCKET_BACKUP",
        "S3_BUCKET_COVERS",
        "S3_BUCKET_FEEDBACK",
        "S3_SSE",
        "S3_SSE_KMS_KEY_ID",
        "RCLONE_COVERS_REMOTE",
        "RCLONE_FEEDBACK_REMOTE",
        "RCLONE_REMOTE_ARCHIVE",
        "RCLONE_REMOTE_FAST",
    ):
        monkeypatch.delenv(name, raising=False)
    S3Service.reset_instances()
    yield
    S3Service.reset_instances()


def _configured(role: str) -> S3Service:
    """Build a service that reports itself configured, with a stub client."""
    service = S3Service(role, access_key="AKIAEXAMPLE", secret_key="s3cr3t-value")
    service._bucket = f"iqoqo-{role}"  # pylint: disable=protected-access
    return service


# ── Configuration ────────────────────────────────────────────────────────────


def test_unknown_bucket_role_is_rejected() -> None:
    """An unknown role must fail loudly, not default to some bucket."""
    with pytest.raises(S3ConfigurationError, match="Unknown S3 bucket role"):
        S3Service("nonsense")


def test_invalid_addressing_style_is_rejected() -> None:
    """A typo in S3_ADDRESSING_STYLE must not silently fall back to virtual."""
    with pytest.raises(S3ConfigurationError, match="S3_ADDRESSING_STYLE"):
        S3Service(BUCKET_COVERS, addressing_style="pathh")


def test_get_s3_service_returns_none_when_no_bucket(monkeypatch) -> None:
    """Unconfigured deployments must not be treated as misconfigured ones."""
    assert get_s3_service(BUCKET_COVERS) is None


def test_get_s3_service_returns_none_when_bucket_without_credentials(monkeypatch) -> None:
    """A bucket set but no key is a misconfiguration, so nothing is returned."""
    monkeypatch.setenv("S3_BUCKET_COVERS", "iqoqo-covers")
    assert get_s3_service(BUCKET_COVERS) is None


def test_get_s3_service_returns_service_when_fully_configured(monkeypatch) -> None:
    """Bucket plus key is the only state in which remote calls are attempted."""
    monkeypatch.setenv("S3_BUCKET_COVERS", "iqoqo-covers")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAEXAMPLE")
    service = get_s3_service(BUCKET_COVERS)
    assert service is not None
    assert service.bucket == "iqoqo-covers"


def test_bucket_without_prefix_role_is_not_accepted() -> None:
    """Roles are explicit; there is no ambient 'default bucket'."""
    with pytest.raises(S3ConfigurationError):
        S3Service("", access_key="k", secret_key="s")


# ── Key construction: the traversal control ──────────────────────────────────


@pytest.mark.parametrize(
    "filename",
    [
        "../../etc/passwd",
        "..%2f..%2fetc",
        "a/b.jpg",
        "a\\b.jpg",
        "-rf",
        ".hidden.jpg",
        "",
        "with space.jpg",
        "with\nnewline.jpg",
        "x" * 256,
    ],
)
def test_unsafe_filenames_are_rejected(filename: str) -> None:
    """A filename that is not a single safe path component must be refused."""
    with pytest.raises(ValueError, match="Unsafe object key component"):
        S3Service.build_key("covers", filename)


def test_legal_filename_is_accepted() -> None:
    """Realistic cover and backup names must keep working."""
    assert S3Service.build_key("covers", "work_123_dalle.jpg") == "covers/work_123_dalle.jpg"
    assert S3Service.build_key("archives", "iqoqo-2026-09-29.tar.gz") == "archives/iqoqo-2026-09-29.tar.gz"


def test_each_role_uses_a_distinct_prefix() -> None:
    """Roles must not collide, so clearing one cannot touch another."""
    service = _configured(BUCKET_COVERS)
    assert service.key_for("x.jpg") == "covers/x.jpg"

    feedback = _configured(BUCKET_FEEDBACK)
    assert feedback.key_for("x.jpg") == "feedback/x.jpg"

    backup = _configured(BUCKET_BACKUP)
    assert backup.key_for("x.tar.gz") == "archives/x.tar.gz"


def test_key_for_rejects_traversal_for_every_role() -> None:
    """The guard is applied by the role helpers, not only by build_key."""
    for role in (BUCKET_COVERS, BUCKET_FEEDBACK, BUCKET_BACKUP):
        with pytest.raises(ValueError):
            _configured(role).key_for("../../escape.jpg")


# ── Credential hygiene ───────────────────────────────────────────────────────


def test_secrets_never_reach_exception_messages() -> None:
    """The raised error must not embed the secret key or the request signature."""

    class ExplodingClient:
        def upload_file(self, *_args, **_kwargs):
            raise ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "bad signature AKIAEXAMPLE s3cr3t-value"}},
                "PutObject",
            )

    service = _configured(BUCKET_BACKUP)
    service._client = ExplodingClient()  # pylint: disable=protected-access

    with pytest.raises(S3UploadError) as excinfo:
        service.upload_file("/tmp/does-not-matter", service.key_for("x.tar.gz"))

    message = str(excinfo.value)
    assert "s3cr3t-value" not in message
    assert "AKIAEXAMPLE" not in message
    # The service error code is kept, so the cause remains diagnosable.
    assert "x.tar.gz" in message


def test_download_error_carries_the_code_for_the_caller(caplog) -> None:
    """Download failures log the code, never the raw exception text."""

    class ExplodingClient:
        def get_object(self, *_args, **_kwargs):
            raise ClientError({"Error": {"Code": "AccessDenied", "Message": "s3cr3t-value"}}, "GetObject")

    service = _configured(BUCKET_FEEDBACK)
    service._client = ExplodingClient()  # pylint: disable=protected-access

    with caplog.at_level(logging.WARNING), pytest.raises(S3DownloadError) as excinfo:
        service.get_bytes(service.key_for("x.jpg"))

    assert "s3cr3t-value" not in caplog.text
    assert "AccessDenied" in caplog.text
    # The code is what lets the API return 404 vs 502 without re-inspecting
    # the chained exception, which would leak the signature it must not expose.
    assert excinfo.value.code == "AccessDenied"


def test_transport_failure_is_not_reported_as_a_service_code() -> None:
    """A network fault must not be mistaken for a service-side refusal."""

    class OfflineClient:
        def get_object(self, *_args, **_kwargs):
            raise EndpointConnectionError(endpoint_url="https://s3.example")

    service = _configured(BUCKET_FEEDBACK)
    service._client = OfflineClient()  # pylint: disable=protected-access

    with pytest.raises(S3DownloadError) as excinfo:
        service.get_bytes(service.key_for("x.jpg"))

    assert excinfo.value.code == "transport"


# ── Client construction ──────────────────────────────────────────────────────


def test_missing_bucket_raises_a_named_error() -> None:
    """A service built without a bucket must say which variable to set."""
    service = S3Service(BUCKET_COVERS, access_key="k", secret_key="s")
    with pytest.raises(S3NotConfiguredError, match="S3_BUCKET_COVERS"):
        service._get_client()  # pylint: disable=protected-access


def test_client_is_built_once_and_reused(monkeypatch) -> None:
    """Connection pooling only works if the client is not rebuilt per call."""
    service = _configured(BUCKET_COVERS)
    fake = object()
    monkeypatch.setattr("app.core.s3_service.boto3.client", lambda *_a, **_k: fake)

    assert service._get_client() is fake  # pylint: disable=protected-access
    assert service._get_client() is fake  # pylint: disable=protected-access


def test_path_style_addressing_is_passed_through(monkeypatch) -> None:
    """MinIO and other gateways need path-style addressing, not AWS's default."""
    captured = {}

    def fake_client(_service, **kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr("app.core.s3_service.boto3.client", fake_client)

    service = S3Service(
        BUCKET_COVERS,
        endpoint_url="https://minio.example",
        addressing_style="path",
        access_key="k",
        secret_key="s",
    )
    service._bucket = "iqoqo-covers"  # pylint: disable=protected-access
    service._get_client()  # pylint: disable=protected-access

    assert captured["endpoint_url"] == "https://minio.example"
    assert captured["config"].s3["addressing_style"] == "path"


def test_timeouts_are_always_explicit(monkeypatch) -> None:
    """boto3's default timeouts can exceed the reverse proxy read timeout."""
    captured = {}
    monkeypatch.setattr("app.core.s3_service.boto3.client", lambda *_a, **k: captured.update(k) or object())

    service = _configured(BUCKET_COVERS)
    service._get_client()  # pylint: disable=protected-access

    config = captured["config"]
    assert config.connect_timeout == 5
    assert config.read_timeout == 30
    # Standard mode retries transient 5xx without duplicating non-idempotent writes.
    assert config.retries == {"mode": "standard", "max_attempts": 3}


# ── Server-side encryption ───────────────────────────────────────────────────


def test_no_sse_args_when_unset(monkeypatch) -> None:
    """SSE is opt-in, because not every S3-compatible provider implements it."""
    monkeypatch.delenv("S3_SSE", raising=False)
    assert _configured(BUCKET_BACKUP)._extra_args() == {}  # pylint: disable=protected-access


def test_sse_args_included_when_set(monkeypatch) -> None:
    """Operator-selected encryption must reach the S3 call."""
    monkeypatch.setenv("S3_SSE", "AES256")
    assert _configured(BUCKET_BACKUP)._extra_args() == {"ServerSideEncryption": "AES256"}  # pylint: disable=protected-access


def test_kms_key_only_sent_for_kms(monkeypatch) -> None:
    """A KMS key id sent with AES256 is rejected by S3, so it is gated."""
    monkeypatch.setenv("S3_SSE", "AES256")
    monkeypatch.setenv("S3_SSE_KMS_KEY_ID", "key-1")
    assert "SSEKMSKeyId" not in _configured(BUCKET_BACKUP)._extra_args()  # pylint: disable=protected-access

    monkeypatch.setenv("S3_SSE", "aws:kms")
    assert _configured(BUCKET_BACKUP)._extra_args()["SSEKMSKeyId"] == "key-1"  # pylint: disable=protected-access


# ── Operations ───────────────────────────────────────────────────────────────


class RecordingClient:
    """Minimal stand-in capturing calls and optionally raising."""

    def __init__(self, raises: Exception | None = None, body: bytes = b"") -> None:
        self.raises = raises
        self.body = body
        self.calls: list[tuple[str, tuple, dict]] = []

    def _record(self, name: str, args: tuple, kwargs: dict) -> None:
        self.calls.append((name, args, kwargs))
        if self.raises:
            raise self.raises

    def upload_file(self, *args, **kwargs):
        self._record("upload_file", args, kwargs)

    def put_object(self, *args, **kwargs):
        self._record("put_object", args, kwargs)

    def get_object(self, *args, **kwargs):
        self._record("get_object", args, kwargs)
        return {"Body": type("B", (), {"read": staticmethod(lambda: self.body)})()}


def test_upload_file_passes_sse_and_content_type(monkeypatch) -> None:
    """Encryption and MIME type must be applied on the write path."""
    monkeypatch.setenv("S3_SSE", "AES256")
    service = _configured(BUCKET_COVERS)
    client = RecordingClient()
    service._client = client  # pylint: disable=protected-access

    service.upload_file("/covers/x.jpg", "covers/x.jpg", content_type="image/jpeg")

    _, _, kwargs = client.calls[0]
    assert kwargs["ExtraArgs"]["ServerSideEncryption"] == "AES256"
    assert kwargs["ExtraArgs"]["ContentType"] == "image/jpeg"


def test_cache_miss_returns_none_instead_of_raising() -> None:
    """A cache lookup must never fail a request that local storage can serve."""

    class MissingClient:
        def download_file(self, *_a, **_k):
            raise ClientError({"Error": {"Code": "NoSuchKey", "Message": "gone"}}, "GetObject")

    service = _configured(BUCKET_COVERS)
    service._client = MissingClient()  # pylint: disable=protected-access
    assert service.download_to_file_or_none("covers/x.jpg", "/tmp/x.jpg") is None


def test_delete_of_missing_object_is_not_an_error() -> None:
    """Idempotent deletes matter for retention passes that may retry."""

    class MissingClient:
        def delete_object(self, *_a, **_k):
            raise ClientError({"Error": {"Code": "NoSuchKey", "Message": "gone"}}, "DeleteObject")

    service = _configured(BUCKET_FEEDBACK)
    service._client = MissingClient()  # pylint: disable=protected-access
    service.delete_object("feedback/x.jpg")  # must not raise


def test_list_keys_paginates(monkeypatch) -> None:
    """A truncated first page would make a retention pass silently under-delete."""

    class PaginatingClient:
        def get_paginator(self, _name):
            class P:
                def paginate(self, **_kwargs):
                    return [
                        {"Contents": [{"Key": "archives/a"}, {"Key": "archives/b"}]},
                        {"Contents": [{"Key": "archives/c"}]},
                    ]

            return P()

    service = _configured(BUCKET_BACKUP)
    service._client = PaginatingClient()  # pylint: disable=protected-access
    assert service.list_keys() == ["archives/a", "archives/b", "archives/c"]


# ── Legacy rclone migration warning ──────────────────────────────────────────


def test_legacy_rclone_env_is_reported_as_disabled(caplog, monkeypatch) -> None:
    """An operator who left RCLONE_* set must be told remote storage is off."""
    import app.core.s3_service as s3_module

    s3_module._warned_legacy.clear()  # pylint: disable=protected-access
    monkeypatch.setenv("RCLONE_COVERS_REMOTE", "iqoqo-s3-cache")
    with caplog.at_level(logging.WARNING):
        s3_module.warn_if_legacy_rclone_configured(BUCKET_COVERS)
    assert "RCLONE_COVERS_REMOTE" in caplog.text
    assert "S3_BUCKET_COVERS" in caplog.text


def test_no_warning_when_s3_replacement_is_present(caplog, monkeypatch) -> None:
    """A migrated deployment must not be nagged about a leftover variable."""
    import app.core.s3_service as s3_module

    s3_module._warned_legacy.clear()  # pylint: disable=protected-access
    monkeypatch.setenv("RCLONE_COVERS_REMOTE", "iqoqo-s3-cache")
    monkeypatch.setenv("S3_BUCKET_COVERS", "iqoqo-covers")
    with caplog.at_level(logging.WARNING):
        s3_module.warn_if_legacy_rclone_configured(BUCKET_COVERS)
    assert "RCLONE_COVERS_REMOTE" not in caplog.text


def test_warn_if_legacy_is_importable_from_package() -> None:
    """The helper is part of the call-site contract, so keep the name stable."""
    assert callable(warn_if_legacy_rclone_configured)

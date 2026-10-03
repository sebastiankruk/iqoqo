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
#
"""Native S3 object storage client, replacing the `rclone` CLI subprocess.

Why this exists (MOD-OPS / OpenSpec ``devops-infrastructure-updates`` §3):

The previous implementation shelled out to `rclone` via
``subprocess.run(["rclone", ...])``. That had three structural problems:

1. **Credential exposure.** Every container that used remote storage had a
   plaintext ``rclone.conf`` bind-mounted into its filesystem
   (``${HOME}/.config/rclone/rclone.conf``), so the S3 access key and secret
   existed as a file inside the container. This module is configured purely
   from environment variables and needs no mounted file.
2. **Process boundary.** Each call forked a process, which under gunicorn's
   synchronous worker model blocked a request thread for the duration of a
   network round-trip, and leaked processes if a call was interrupted.
3. **No typed failure mode.** Errors surfaced as ``CalledProcessError`` with
   stderr text, and callers had to guess whether a missing remote was a
   misconfiguration or a transient network fault.

Configuration is via standard, provider-neutral environment variables so the
same deployment works against AWS S3, MinIO, Cloudflare R2, Wasabi, Backblaze
B2, and Oracle Cloud Object Storage without code changes:

    AWS_ACCESS_KEY_ID       access key
    AWS_SECRET_ACCESS_KEY   secret key
    AWS_SESSION_TOKEN       optional, for STS/assumed-role deployments
    S3_ENDPOINT_URL         endpoint; omit for real AWS
    S3_REGION_NAME          region; defaults to us-east-1
    S3_ADDRESSING_STYLE     virtual (default) | path — MinIO and most
                            self-hosted gateways require ``path``
    S3_BUCKET_BACKUP        backups / archive rotation
    S3_BUCKET_COVERS        shared cover cache
    S3_BUCKET_FEEDBACK      feedback screenshots
    S3_SSE                  server-side encryption algorithm
    S3_SSE_KMS_KEY_ID       KMS key id, when S3_SSE is aws:kms

When S3 is not configured, every method is a no-op that reports "not
configured" rather than raising, so a self-hosted instance that does not use
remote storage keeps working unchanged.
"""

from __future__ import annotations

import logging
import os
import re
import threading
from typing import Any

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError, EndpointConnectionError

logger = logging.getLogger(__name__)

# Bucket roles. Kept as an enum-like set of string constants so a call site must
# name which bucket it means; there is deliberately no "default bucket" fallback,
# because silently writing backups to the covers bucket would be a data-loss
# incident waiting to happen.
BUCKET_BACKUP = "backup"
BUCKET_COVERS = "covers"
BUCKET_FEEDBACK = "feedback"

_VALID_BUCKETS = frozenset({BUCKET_BACKUP, BUCKET_COVERS, BUCKET_FEEDBACK})

# Object key prefixes, kept separate from the bucket so a single bucket can be
# used for several roles without collisions, and so clearing one role's objects
# cannot touch another's.
# ``archives`` for backups matches the layout the previous in-container rclone
# remote used (``get_rclone_target(remote, "archives")`` resolved to
# ``<remote>:archives``). Note the container no longer has an archiving task --
# that was removed as unreachable -- so the backup role's only consumer is
# scripts/cloud_backup.sh, which passes its own S3_KEY_PREFIX and so normally
# overrides this prefix entirely.
_PREFIXES = {
    BUCKET_COVERS: "covers",
    BUCKET_FEEDBACK: "feedback",
    BUCKET_BACKUP: "archives",
}

# S3 keys are flat strings, not directories, but every object key here is
# built by joining a prefix and a caller-supplied filename. Filenames reach us
# from user input (uploaded cover names, feedback screenshot names) and from the
# filesystem. Anything that could change the meaning of the key -- a slash, a
# dot segment, a leading dash, control characters -- is rejected rather than
# sanitised, because a silently rewritten key would make the caller believe it
# had written somewhere it did not.
_SAFE_KEY_CHARS = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,254}$")

# Refuse to build keys that could escape the intended prefix. Combined with the
# character allowlist this makes traversal structurally impossible rather than
# filtered.
_FORBIDDEN_KEY_FRAGMENTS = ("..", "//", "\\", "\x00")


class S3ConfigurationError(RuntimeError):
    """Raised when S3 is configured in a way that cannot work."""


class S3NotConfiguredError(RuntimeError):
    """Raised when an operation requires S3 but no credentials are present."""


class S3UploadError(RuntimeError):
    """Raised when an object could not be uploaded."""


class S3DownloadError(RuntimeError):
    """Raised when an object could not be read.

    Attributes:
        code: The S3 service error code (``NoSuchKey``, ``AccessDenied``, ...)
            or ``"transport"`` when the request never reached the service. This
            is the only diagnostic carried, deliberately: botocore's exception
            text can embed the request signature. Callers branch on it to
            distinguish a genuinely absent object (a 404) from a reachable-but-
            failing backend (a 502), which are different operational problems.
    """

    def __init__(self, message: str, code: str = "transport") -> None:
        super().__init__(message)
        self.code = code


def _error_code(exc: BaseException) -> str:
    """Extract the S3 service error code from a botocore exception.

    Returns ``"transport"`` when the request never reached the service, so a
    network fault is never confused with a service-side refusal.
    """
    if isinstance(exc, ClientError):
        return str(exc.response.get("Error", {}).get("Code", "unknown"))
    return "transport"


def _env_flag(name: str, default: bool = False) -> bool:
    """Read a boolean environment variable, tolerating absent and junk values."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"true", "1", "yes", "on"}


class S3Service:
    """Thread-safe, lazily-initialised S3 client for a single process.

    A single ``boto3.client`` is shared per credential/bucket configuration. boto3
    clients are documented as safe to share across threads provided the client is
    created after threads exist, and the underlying urllib3 pool is what makes
    reuse worthwhile — a new client per call would defeat connection pooling and
    leak sockets under load.

    Instances are cached per configuration so repeated ``S3Service()`` calls from
    different modules do not each build a pool.
    """

    _instances: dict[tuple[str, ...], S3Service] = {}
    _instances_lock = threading.Lock()

    def __init__(
        self,
        bucket_role: str,
        *,
        endpoint_url: str | None = None,
        region_name: str | None = None,
        addressing_style: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        session_token: str | None = None,
    ) -> None:
        if bucket_role not in _VALID_BUCKETS:
            raise S3ConfigurationError(f"Unknown S3 bucket role {bucket_role!r}; expected one of {sorted(_VALID_BUCKETS)}")

        self.bucket_role = bucket_role
        self.endpoint_url = (endpoint_url or "").strip() or None
        self.region_name = (region_name or "us-east-1").strip() or "us-east-1"
        self.addressing_style = (addressing_style or "virtual").strip().lower()
        if self.addressing_style not in {"virtual", "path"}:
            raise S3ConfigurationError(f"S3_ADDRESSING_STYLE must be 'virtual' or 'path', got {addressing_style!r}")

        # Credentials are read into instance attributes but never logged, and
        # never included in any exception message we construct ourselves.
        self._access_key = access_key
        self._secret_key = secret_key
        self._session_token = session_token

        self._bucket = self._resolve_bucket(bucket_role)
        self._client: Any | None = None
        self._client_lock = threading.Lock()

    # ── Configuration ─────────────────────────────────────────────────────

    @classmethod
    def get_instance(cls, bucket_role: str) -> S3Service:
        """Return a shared instance for *bucket_role*, or ``None`` when unconfigured.

        The cache key includes the endpoint, region and addressing style so that a
        process which talks to two differently-configured endpoints does not
        silently reuse the wrong client.
        """
        endpoint = os.environ.get("S3_ENDPOINT_URL", "").strip()
        region = os.environ.get("S3_REGION_NAME", "us-east-1").strip()
        style = os.environ.get("S3_ADDRESSING_STYLE", "virtual").strip().lower()
        key = (bucket_role, endpoint, region, style)

        with cls._instances_lock:
            existing = cls._instances.get(key)
            if existing is not None:
                return existing
            instance = cls.from_environment(bucket_role)
            cls._instances[key] = instance
            return instance

    @classmethod
    def from_environment(cls, bucket_role: str) -> S3Service:
        """Build an instance purely from environment variables."""
        return cls(
            bucket_role,
            endpoint_url=os.environ.get("S3_ENDPOINT_URL"),
            region_name=os.environ.get("S3_REGION_NAME"),
            addressing_style=os.environ.get("S3_ADDRESSING_STYLE"),
            access_key=os.environ.get("AWS_ACCESS_KEY_ID"),
            secret_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            session_token=os.environ.get("AWS_SESSION_TOKEN"),
        )

    @classmethod
    def reset_instances(cls) -> None:
        """Drop cached clients. Intended for tests and for credential rotation."""
        with cls._instances_lock:
            cls._instances.clear()

    @staticmethod
    def _resolve_bucket(bucket_role: str) -> str | None:
        env_name = f"S3_BUCKET_{bucket_role.upper()}"
        value = os.environ.get(env_name, "").strip()
        return value or None

    def is_configured(self) -> bool:
        """Whether this role has both a bucket and credentials available.

        Both halves are required. A bucket without credentials means the
        operator set the variable but not the key, and silently treating that as
        "remote storage disabled" would hide a misconfiguration; it is reported
        as unconfigured here and the call sites log it distinctly.
        """
        return bool(self._bucket and (self._access_key or _env_flag("AWS_ALLOW_ANONYMOUS", False)))

    @property
    def bucket(self) -> str | None:
        """Configured bucket name, or ``None``."""
        return self._bucket

    # ── Client construction ───────────────────────────────────────────────

    def _get_client(self) -> Any:
        """Return the shared boto3 client, building it on first use."""
        if self._client is not None:
            return self._client
        with self._client_lock:
            if self._client is not None:
                return self._client

            if not self._bucket:
                raise S3NotConfiguredError(f"No bucket configured for role '{self.bucket_role}'; set S3_BUCKET_{self.bucket_role.upper()}.")

            # Explicit timeouts. boto3's defaults are generous enough that a
            # half-open connection can block a gunicorn worker past the
            # reverse proxy's 120s read timeout, and the failure then looks like
            # an application hang rather than a storage outage.
            boto_config = BotoConfig(
                signature_version="s3v4",
                connect_timeout=int(os.environ.get("S3_CONNECT_TIMEOUT", "5")),
                read_timeout=int(os.environ.get("S3_READ_TIMEOUT", "30")),
                max_pool_connections=int(os.environ.get("S3_MAX_POOL_CONNECTIONS", "10")),
                # Standard mode retries the transient 5xx/connection errors that
                # an S3-compatible gateway produces under load. Legacy mode is
                # explicitly avoided: it retries on non-idempotent operations,
                # which can leave duplicate objects after a partial failure.
                retries={"mode": "standard", "max_attempts": 3},
                s3={"addressing_style": self.addressing_style},
            )

            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                region_name=self.region_name,
                aws_access_key_id=self._access_key,
                aws_secret_access_key=self._secret_key,
                aws_session_token=self._session_token,
                config=boto_config,
            )
            return self._client

    # ── Key handling ──────────────────────────────────────────────────────

    @staticmethod
    def build_key(prefix: str, filename: str) -> str:
        """Join *prefix* and *filename* into a validated object key.

        Raises:
            ValueError: if *filename* is not a safe single path component.
        """
        if not filename or not _SAFE_KEY_CHARS.match(filename):
            raise ValueError(f"Unsafe object key component: {filename!r}")
        for fragment in _FORBIDDEN_KEY_FRAGMENTS:
            if fragment in filename:
                raise ValueError(f"Unsafe object key component: {filename!r}")
        return f"{prefix}/{filename}" if prefix else filename

    def key_for(self, filename: str) -> str:
        """Build the object key for *filename* in this service's role."""
        return self.build_key(_PREFIXES.get(self.bucket_role, ""), filename)

    # ── Server-side encryption ────────────────────────────────────────────

    def _extra_args(self) -> dict[str, Any]:
        """Server-side encryption arguments, when configured.

        Backups and cover caches are restorable user data; encrypting at rest
        server-side means a compromised bucket or a misconfigured provider
        lifecycle policy cannot expose them in plaintext. The algorithm is
        opt-in because not every S3-compatible provider implements SSE, and a
        hard requirement would break MinIO and Oracle Object Storage defaults.
        """
        sse = os.environ.get("S3_SSE", "").strip()
        if not sse:
            return {}
        args: dict[str, Any] = {"ServerSideEncryption": sse}
        kms_key = os.environ.get("S3_SSE_KMS_KEY_ID", "").strip()
        if kms_key and sse == "aws:kms":
            args["SSEKMSKeyId"] = kms_key
        return args

    # ── Operations ────────────────────────────────────────────────────────

    def upload_file(self, local_path: str, key: str, *, content_type: str | None = None) -> str:
        """Upload *local_path* to *key*.

        Uses ``upload_file`` rather than ``put_object`` so large backup archives
        stream in bounded chunks instead of being read into memory whole.

        Args:
            local_path: Absolute path to the local file.
            key: Object key. Must already be validated.
            content_type: Optional MIME type for the stored object.

        Returns:
            The object key written.

        Raises:
            S3UploadError: on any transport or service error.
        """
        extra: dict[str, Any] = dict(self._extra_args())
        if content_type:
            extra["ContentType"] = content_type

        try:
            self._get_client().upload_file(local_path, self._bucket, key, ExtraArgs=extra or None)
        except (ClientError, BotoCoreError, EndpointConnectionError, OSError) as exc:
            # The exception text can embed the endpoint and, for some providers,
            # the request signature. Log the operation and the type, never the
            # raw exception, and never the credentials.
            logger.error(
                "S3 upload failed (role=%s bucket=%s key=%s): %s: %s",
                self.bucket_role,
                self._bucket,
                key,
                type(exc).__name__,
                getattr(exc, "response", {}).get("Error", {}).get("Code", "unknown"),
            )
            raise S3UploadError(f"Failed to upload {key} to bucket {self._bucket}") from exc
        return key

    def upload_bytes(self, data: bytes, key: str, *, content_type: str | None = None) -> str:
        """Upload in-memory *data* to *key*.

        Raises:
            S3UploadError: on any transport or service error.
        """
        extra: dict[str, Any] = dict(self._extra_args())
        if content_type:
            extra["ContentType"] = content_type

        try:
            self._get_client().put_object(Bucket=self._bucket, Key=key, Body=data, **extra)
        except (ClientError, BotoCoreError, EndpointConnectionError) as exc:
            logger.error(
                "S3 put failed (role=%s bucket=%s key=%s): %s: %s",
                self.bucket_role,
                self._bucket,
                key,
                type(exc).__name__,
                getattr(exc, "response", {}).get("Error", {}).get("Code", "unknown"),
            )
            raise S3UploadError(f"Failed to store {key} in bucket {self._bucket}") from exc
        return key

    def download_file(self, key: str, local_path: str) -> str:
        """Download *key* to *local_path*.

        Raises:
            S3DownloadError: on any transport or service error, including a
                missing object.
        """
        try:
            self._get_client().download_file(self._bucket, key, local_path)
        except (ClientError, BotoCoreError, EndpointConnectionError, OSError) as exc:
            code = getattr(exc, "response", {}).get("Error", {}).get("Code", "unknown")
            logger.warning(
                "S3 download failed (role=%s bucket=%s key=%s): %s: %s",
                self.bucket_role,
                self._bucket,
                key,
                type(exc).__name__,
                code,
            )
            raise S3DownloadError(f"Failed to download {key} from bucket {self._bucket}") from exc
        return local_path

    def get_bytes(self, key: str) -> bytes:
        """Fetch *key* and return its bytes.

        Raises:
            S3DownloadError: on any transport or service error.
        """
        try:
            response = self._get_client().get_object(Bucket=self._bucket, Key=key)
            # botocore's StreamingBody.read() is untyped; the cast is where the
            # bytes contract is asserted, since a truncated body would surface
            # as a short read rather than an exception.
            data: bytes = response["Body"].read()
            return data
        except (ClientError, BotoCoreError, EndpointConnectionError, KeyError) as exc:
            code = _error_code(exc)
            logger.warning(
                "S3 get failed (role=%s bucket=%s key=%s): %s: %s",
                self.bucket_role,
                self._bucket,
                key,
                type(exc).__name__,
                code,
            )
            raise S3DownloadError(f"Failed to read {key} from bucket {self._bucket}", code=code) from exc

    def download_to_file_or_none(self, key: str, local_path: str) -> str | None:
        """Best-effort download for cache-population paths.

        A miss is an expected, routine outcome when populating a shared cache, so
        this returns ``None`` instead of raising. A genuine transport failure is
        also treated as a miss by design: a cache lookup must never fail a
        request that can still be served from local storage.
        """
        try:
            return self.download_file(key, local_path)
        except S3DownloadError:
            return None

    def object_exists(self, key: str) -> bool:
        """Whether *key* is present. Any error is reported as "absent"."""
        try:
            self._get_client().head_object(Bucket=self._bucket, Key=key)
        except (ClientError, BotoCoreError, EndpointConnectionError):
            return False
        return True

    def delete_object(self, key: str) -> None:
        """Delete *key*. Missing objects are not an error.

        Raises:
            S3UploadError: on a non-404 service or transport error.
        """
        try:
            self._get_client().delete_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            code = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
            if code not in {"404", "NoSuchKey", "NotFound"}:
                logger.error("S3 delete failed (role=%s key=%s): %s", self.bucket_role, key, code)
                raise S3UploadError(f"Failed to delete {key} from bucket {self._bucket}") from exc
        except (BotoCoreError, EndpointConnectionError) as exc:
            raise S3UploadError(f"Failed to delete {key} from bucket {self._bucket}") from exc

    def list_keys(self, prefix: str = "") -> list[str]:
        """List object keys under *prefix*.

        Pagination is handled so a large bucket does not return a truncated first
        page, which would otherwise make a retention or cleanup pass silently
        under-delete.

        Raises:
            S3UploadError: on a listing failure.
        """
        keys: list[str] = []
        try:
            paginator = self._get_client().get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    keys.append(obj["Key"])
        except (ClientError, BotoCoreError, EndpointConnectionError) as exc:
            code = getattr(exc, "response", {}).get("Error", {}).get("Code", "unknown")
            logger.error("S3 list failed (role=%s prefix=%s): %s", self.bucket_role, prefix, code)
            raise S3UploadError(f"Failed to list objects in bucket {self._bucket}") from exc
        return keys


def get_s3_service(bucket_role: str) -> S3Service | None:
    """Return a shared :class:`S3Service` for *bucket_role*, or ``None``.

    ``None`` means remote storage is not configured, which every call site treats
    as "carry on locally". Returning ``None`` rather than an unconfigured service
    keeps the check at the call site explicit and greppable.
    """
    try:
        service = S3Service.get_instance(bucket_role)
    except S3ConfigurationError:
        logger.exception("Invalid S3 configuration for role %s; remote storage disabled", bucket_role)
        return None
    if not service.is_configured():
        return None
    return service


# Maps each legacy rclone variable to the S3 variables that replace it, so the
# warning can name what the operator actually has to set.
_LEGACY_RCLONE_ENV = {
    "RCLONE_COVERS_REMOTE": (BUCKET_COVERS, "S3_BUCKET_COVERS"),
    "RCLONE_FEEDBACK_REMOTE": (BUCKET_FEEDBACK, "S3_BUCKET_FEEDBACK"),
    "RCLONE_REMOTE_ARCHIVE": (BUCKET_BACKUP, "S3_BUCKET_BACKUP"),
    "RCLONE_REMOTE_FAST": (BUCKET_BACKUP, "S3_BUCKET_BACKUP"),
}

_warned_legacy: set[str] = set()


def warn_if_legacy_rclone_configured(bucket_role: str) -> None:
    """Warn once per process when a role is served by rclone config, not S3.

    A deployment upgrading from the rclone implementation keeps its
    ``RCLONE_*_REMOTE`` variables in ``.env`` for a while. Without this, remote
    storage would simply stop working at the next backup rotation or cover-cache
    miss, and the first symptom would be a missing archive discovered weeks later.
    Raising the signal here, at the call site, is the difference between "remote
    storage is intentionally off" and "remote storage is silently broken".
    """
    for legacy_var, (role, replacement) in _LEGACY_RCLONE_ENV.items():
        if role != bucket_role:
            continue
        if not os.environ.get(legacy_var, "").strip():
            continue
        if os.environ.get(replacement, "").strip():
            continue
        if legacy_var in _warned_legacy:
            continue
        _warned_legacy.add(legacy_var)
        logger.warning(
            "%s is set but %s is not. Remote storage for the %r role is DISABLED. "
            "iqoqo no longer shells out to rclone and no longer mounts rclone.conf; "
            "set %s (plus AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY) or unset %s to "
            "acknowledge that remote storage is intentionally off.",
            legacy_var,
            replacement,
            bucket_role,
            replacement,
            legacy_var,
        )

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
"""Application-wide redaction of credentials and single-use tokens from logs.

Logging a token is a slow-motion credential leak: the token lands in a log
aggregator, in a backup of the aggregator, and in the retention of both, none of
which are access-controlled the way the mail server is.  It also survives the
user changing their address, which is exactly when a stale link should stop
working.

The project had no redaction layer at all -- :mod:`app.core.telemetry` redacts
the telemetry it exports, and everything else was left to the discipline of
whoever wrote the call.  This module is that missing layer.

It works as a :class:`logging.Filter` installed on the root handler by
:func:`install_redaction`, so it covers code that does not exist yet.  Three
kinds of value are scrubbed:

* **Token-bearing query parameters.**  ``/confirm?token=abc`` becomes
  ``/confirm?token=***``.  The key is matched by name, so an unrecognised
  parameter that turns out to be sensitive later is one line away from covered.
* **Known credential values.**  Live secrets registered via
  :func:`register_secret` are replaced wherever they appear, which catches the
  case parameter-name matching misses: a token pasted into a message, or a URL
  built somewhere that never had a ``token=`` in it.
* **JWS-shaped strings.**  A three-segment base64url blob is a JWT by
  construction, and the app's own session tokens match.  Scrubbed structurally,
  so the log does not depend on having been told the value.

Replacing with a fixed marker rather than removing keeps a log line's shape
intelligible -- an operator can still see that *something* was redacted, which
is itself the signal that a credential handler misbehaved.
"""

from __future__ import annotations

import logging
import re

#: The value substituted for anything scrubbed.
REDACTED = "***REDACTED***"

#: Query/JSON/form keys whose value is a credential.  Matched
#: case-insensitively as a substring, so ``code``, ``code_challenge`` and
#: ``authorization_code`` are all covered by the single entry ``code``.
SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "token",
        "code_verifier",
        "code_challenge",
        "secret",
        "password",
        "passwd",
        "passphrase",
        "api_key",
        "apikey",
        "access_token",
        "refresh_token",
        "client_secret",
        "signature",
        "credential",
    }
)

#: ``key=value`` / ``key: value`` / ``"key":"value"`` where *key* is sensitive.
_KEY_VALUE_RE = re.compile(
    r"(?P<key>\b(?:" + "|".join(sorted(SENSITIVE_KEYS, key=len, reverse=True)) + r")\b)"
    r"(?P<sep>\s*[=:]\s*|\s*=>\s*)"
    r"(?P<quote>[\"']?)"
    r"(?P<value>[^\s\"'&,;)}]+)"
    r"(?P=quote)",
    re.IGNORECASE,
)

#: Three dot-separated base64url segments: a JWS compact serialisation.  The
#: signature segment is what matters, and it is at least 16 characters in every
#: real token, so requiring it keeps ordinary prose (``a.b.c``) from being
#: mangled.
_JWS_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{16,}\b")

#: Live secret values registered at runtime.  Kept in a list rather than a set
#: because a one-character "secret" would redact half the log; anything shorter
#: than :data:`_MIN_SECRET_LENGTH` is refused at registration.
_MIN_SECRET_LENGTH = 12
_secrets: list[str] = []


def register_secret(value: str | None) -> None:
    """Register a live secret so it is scrubbed wherever it appears.

    Intended for the few values that are worth protecting everywhere: the
    application secret, a JWT signing key.  Database-stored provider
    credentials are better protected by not being logged in the first place;
    registering hundreds of those would make the filter's own cost unbounded.

    Args:
        value: The secret.  Values shorter than 12 characters are ignored,
            because a filter that blanks common words destroys more signal than
            it protects.
    """
    if value and len(value) >= _MIN_SECRET_LENGTH and value not in _secrets:
        _secrets.append(value)


def clear_registered_secrets() -> None:
    """Forget every registered secret.  For test isolation."""
    _secrets.clear()


def redact_text(text: str) -> str:
    """Return *text* with every recognised credential replaced.

    Args:
        text: A log message, URL or exception string.

    Returns:
        The scrubbed text.  Equal to the input when nothing matched.
    """
    if not text:
        return text

    redacted = _KEY_VALUE_RE.sub(
        lambda m: f"{m.group('key')}{m.group('sep')}{m.group('quote')}{REDACTED}{m.group('quote')}",
        text,
    )
    redacted = _JWS_RE.sub(REDACTED, redacted)
    for secret in _secrets:
        if secret and secret in redacted:
            redacted = redacted.replace(secret, REDACTED)
    return redacted


class RedactionFilter(logging.Filter):
    """Scrub credentials from a log record's message and arguments.

    Attached to a handler rather than a logger so it applies to records that
    propagate from anywhere, including third-party libraries and Celery workers.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Rewrite *record* in place, redacting message text and arguments.

        Args:
            record: The record about to be emitted.

        Returns:
            Always True: redaction must never suppress a line.  Losing a log
                line because a filter raised would hide exactly the incident a
                filter exists to make safe.
        """
        try:
            if isinstance(record.msg, str):
                record.msg = redact_text(record.msg)
            elif record.msg is not None:
                record.msg = redact_text(str(record.msg))

            if record.args:
                if isinstance(record.args, dict):
                    record.args = {k: redact_text(v) if isinstance(v, str) else v for k, v in record.args.items()}
                elif isinstance(record.args, tuple):
                    record.args = tuple(redact_text(a) if isinstance(a, str) else a for a in record.args)

            # `exc_info` carries the rendered traceback separately, and its text
            # reaches the handler without passing through `msg` or `args`.
            if record.exc_text:
                record.exc_text = redact_text(record.exc_text)
        except Exception:  # pragma: no cover - a filter must never break logging
            return True
        return True


def install_redaction(logger: logging.Logger | None = None) -> None:
    """Install :class:`RedactionFilter` on a logger's handlers.

    Idempotent: safe to call from both the app factory and a Celery worker
    bootstrap, and it will not stack duplicate filters if called twice.

    Args:
        logger: The logger whose handlers to protect.  Defaults to the root
            logger, which is what :func:`app.create_app` configures with
            ``logging.basicConfig(force=True)``.
    """
    target = logger or logging.getLogger()
    for handler in target.handlers:
        if not any(isinstance(f, RedactionFilter) for f in handler.filters):
            handler.addFilter(RedactionFilter())
    if not target.handlers:
        # `basicConfig` has not run yet (a Celery worker that never called
        # create_app).  Attach to the root logger's last-resort handler so the
        # filter is not silently absent.
        target.addHandler(logging.StreamHandler())
        target.handlers[-1].addFilter(RedactionFilter())

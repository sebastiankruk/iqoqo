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
"""
OpenTelemetry span hooks for the Flask application.

This module provides ``request_hook`` and ``response_hook`` callbacks that are
registered with ``opentelemetry-instrumentation-flask`` via ``FlaskInstrumentor``.

The primary concern of ``request_hook`` is **credential hygiene**: the Flask
WSGI environ contains the raw ``HTTP_AUTHORIZATION`` header value which would
otherwise be captured verbatim in the span attributes and shipped to the
telemetry backend.  The hook overwrites the attribute with a ``[REDACTED]``
sentinel before the span is dispatched so that bearer tokens never appear in
traces, regardless of the OpenObserve / OTel Collector retention policy.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def request_hook(span: Any, environ: dict) -> None:
    """Sanitize sensitive WSGI headers before a span is recorded.

    Flask places HTTP request headers in the WSGI ``environ`` dict with an
    ``HTTP_`` prefix (e.g. ``Authorization`` → ``HTTP_AUTHORIZATION``).  The
    OpenTelemetry Flask instrumentation captures these values as span
    attributes.  This hook intercepts that capture and replaces the
    ``Authorization`` header value with ``[REDACTED]`` to prevent credential
    leakage into the tracing backend.

    Parameters
    ----------
    span:
        The active ``opentelemetry.trace.Span`` for the current request.
        The function is a no-op if the span is ``None`` or not recording.
    environ:
        The WSGI environ dictionary for the incoming request.
    """
    # Guard: span may be None or not yet recording (e.g. sampled out).
    if span is None:
        return
    try:
        if not span.is_recording():  # type: ignore[union-attr]
            return
        if environ.get("HTTP_AUTHORIZATION"):
            span.set_attribute("http.request.header.authorization", "[REDACTED]")  # type: ignore[union-attr]
    except Exception:  # pylint: disable=broad-exception-caught
        # Telemetry hooks must never surface exceptions to application code.
        logger.debug("request_hook: failed to redact Authorization header", exc_info=True)


def response_hook(span: Any, status: str, response_headers: list) -> None:
    """Post-response span hook — reserved for future response attribute enrichment.

    Parameters
    ----------
    span:
        The active ``opentelemetry.trace.Span`` (may be ``None``).
    status:
        The HTTP response status string (e.g. ``\"200 OK\"``).
    response_headers:
        List of ``(name, value)`` response header tuples.
    """
    # No-op: reserved for future use (e.g. annotating span with response content-type).

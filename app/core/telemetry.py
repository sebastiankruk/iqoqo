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
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

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
    except (AttributeError, KeyError, TypeError, ValueError, RuntimeError):
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


def init_telemetry(app: Any) -> None:
    """Initialize OpenTelemetry instrumentation hooks for the Flask application.

    Registers ``request_hook`` and ``response_hook`` with ``FlaskInstrumentor``
    if ``opentelemetry-instrumentation-flask`` is installed and active.

    Parameters
    ----------
    app:
        The Flask application instance.
    """
    try:
        from opentelemetry.instrumentation.flask import FlaskInstrumentor

        FlaskInstrumentor().instrument_app(app, request_hook=request_hook, response_hook=response_hook)
    except (ImportError, RuntimeError, TypeError, AttributeError, ValueError) as exc:
        logger.debug("Telemetry hook registration skipped: %s", exc)


def sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
    """Sanitize HTTP request headers by redacting sensitive values.

    Parameters
    ----------
    headers:
        Dictionary of HTTP request headers.

    Returns
    -------
    dict[str, str]
        New dictionary with sensitive header values (like Authorization, keys, secrets)
        replaced with '***REDACTED***'.
    """
    sensitive_keywords = {"authorization", "key", "token", "secret", "cookie", "session"}
    sanitized = {}
    for key, value in headers.items():
        key_lower = key.lower()
        if any(kw in key_lower for kw in sensitive_keywords):
            sanitized[key] = "***REDACTED***"
        else:
            sanitized[key] = str(value)
    return sanitized


def sanitize_url(url: str | None) -> str | None:
    """Sanitize URL query parameters by redacting sensitive parameter values.

    Parameters
    ----------
    url:
        The URL string to sanitize (or None).

    Returns
    -------
    str | None
        Sanitized URL string with sensitive query parameter values replaced with
        '***REDACTED***', or None if input is None or empty.
        Returns '***REDACTED_URL_PARSE_ERROR***' if parsing fails unexpectedly.
    """
    if not url:
        return url

    sensitive_keywords = {"key", "token", "secret", "auth", "signature", "credential"}
    try:
        parsed = urlparse(url)
        if not parsed.query:
            return url
        params = parse_qsl(parsed.query, keep_blank_values=True)
        sanitized_params = []
        for key, val in params:
            key_lower = key.lower()
            if any(kw in key_lower for kw in sensitive_keywords):
                sanitized_params.append((key, "***REDACTED***"))
            else:
                sanitized_params.append((key, val))
        new_query = urlencode(sanitized_params)
        new_parsed = parsed._replace(query=new_query)
        return urlunparse(new_parsed)
    except (TypeError, ValueError, AttributeError):
        logger.debug("sanitize_url: failed to parse URL", exc_info=True)
        return "***REDACTED_URL_PARSE_ERROR***"


def record_outbound_telemetry(service_name: str, headers: dict[str, str], url: str | None = None) -> dict[str, str]:
    """Attach outbound HTTP request headers to active OpenTelemetry span and emit a structured log.

    Parameters
    ----------
    service_name:
        Name of the target external service (e.g. 'Allegro', 'DirectURL').
    headers:
        Dictionary of HTTP request headers sent to the service.
    url:
        Optional request URL for additional tracing context.

    Returns
    -------
    dict[str, str]
        The sanitized headers dictionary.
    """
    sanitized = sanitize_headers(headers)
    sanitized_url = sanitize_url(url) if url else None

    # 1. OpenTelemetry Span Enrichment
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span is not None and hasattr(span, "is_recording") and span.is_recording():  # type: ignore[union-attr]
            for key, value in sanitized.items():
                attr_name = f"http.request.header.{key.lower().replace('-', '_')}"
                span.set_attribute(attr_name, value)  # type: ignore[union-attr]
            if sanitized_url:
                span.set_attribute("http.url", sanitized_url)  # type: ignore[union-attr]
            span.set_attribute("peer.service", service_name)  # type: ignore[union-attr]
    except (ImportError, AttributeError, KeyError, TypeError, ValueError, RuntimeError) as exc:
        logger.debug("Failed to set span attributes in record_outbound_telemetry: %s", exc)

    # 2. Structured Application Log
    log_extra: dict[str, Any] = {f"http.request.header.{k.lower().replace('-', '_')}": v for k, v in sanitized.items()}
    if sanitized_url:
        log_extra["http.url"] = sanitized_url
    log_extra["peer.service"] = service_name

    logger.info("Outbound %s API request", service_name, extra=log_extra)
    return sanitized

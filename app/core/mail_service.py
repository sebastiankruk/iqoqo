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
"""Outbound transactional mail.

iQoQo is self-hosted software, so this boundary speaks plain SMTP and nothing
else.  A provider SDK would have made the feature unavailable to exactly the
deployments that need it most, and the transports operators already run
(Postfix on the same host, or a managed relay they were going to use anyway) are
all reachable over SMTP.

Design points that are load-bearing rather than incidental:

**Nothing connects at startup.**  A deployment that has not configured mail must
still boot, serve its catalogue and accept logins; a missing relay is an
operator problem to fix, not a reason to refuse to start.  The cost is that a
misconfiguration surfaces on first send, which is why every send failure names
the configuration key at fault.

**Every send is bounded by a timeout.**  ``socket_timeout`` and the SMTP
``timeout`` are set from configuration, because the alternative is a gunicorn
worker blocked indefinitely on an unreachable relay -- one hung request per
worker is a total outage, and the nightmare scenario for this stack specifically
is an SMTP black hole rather than a slow query.

**TLS is explicit and never silently downgraded.**  STARTTLS is used by default;
plaintext is possible only by opting out by name, and implicit TLS (SMTPS) is a
separate mutually exclusive mode.  A server that does not offer STARTTLS when it
was asked for it is a failed send, not a plaintext send.

**Addresses and headers are validated, and the sender is not user-controlled.**
  ``From`` comes from configuration alone.  A caller can choose the recipient but
  cannot influence the envelope sender or any other header, which closes the
  header-injection and sender-spoofing paths at the source rather than by
  escaping.

**Content is text.**  Templates render to ``text/plain`` with a single
``text/html`` alternative when one is supplied; there is no attachment support
and no templating of operator data through an HTML engine that could fetch a
remote resource.

Tests inject :class:`RecordingTransport` rather than patching ``smtplib``, so a
test asserts on the message that *would* have gone out without opening a socket.
"""

from __future__ import annotations

import logging
import re
import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid, parseaddr
from typing import Protocol

logger = logging.getLogger(__name__)

#: Refuse anything longer before doing any work.  RFC 5321 caps a path at 256
#: octets including the angle brackets, and the local part at 64.  Generous
#: relative to that, tight enough to bound the regex work.
MAX_ADDRESS_LENGTH = 254

#: Deliberately conservative address shape.  The standard's grammar permits
#: quoted local parts and comments that no real mail provider accepts, so
#: accepting them would mean accepting addresses that bounce.  This rejects
#: them, which also removes every CR/LF and control character from the input
#: before it is used as a header value.
_ADDRESS_RE = re.compile(
    r"\A[A-Za-z0-9!#$%&'*+/=?^_`{|}~.-]{1,64}@[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+\Z"
)

#: SMTP host.  A hostname or an IPv4 literal -- never a URL, never a path, and
#: never a bare ``user:pass@host``.  ``MAIL_HOST`` is operator configuration, so
#: this is a typo guard rather than an injection guard, but a URL pasted by
#: mistake would otherwise produce a confusing port error an hour later.
#:
#: Each dot-separated label must start and end with an alphanumeric, which is
#: what rejects a trailing dot and a leading hyphen. The label rule is repeated
#: per label rather than applied to the whole string, because a single
#: ``[A-Za-z0-9]`` character class spanning the name would be satisfied by the
#: dot itself.
_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
_SMTP_HOST_RE = re.compile(rf"\A(?:{_LABEL}(?:\.{_LABEL})*|[0-9]{{1,3}}(?:\.[0-9]{{1,3}}){{3}})\Z")

#: Bounds on the relay connection.  Both are configurable because a relay on
#: the same LAN and one across an ocean want very different numbers, but neither
#: is allowed to be unbounded.
DEFAULT_TIMEOUT_SECONDS = 10
MIN_TIMEOUT_SECONDS = 1
MAX_TIMEOUT_SECONDS = 120


class MailError(Exception):
    """Base class for mail failures."""


class MailConfigurationError(MailError):
    """Mail is not usable, because it is not configured.

    Distinct from :class:`MailDeliveryError` because the two need different
    operator responses and different user-facing messages: this one means "fix
    the deployment", the other means "the relay is having a bad day and the
    user may retry".
    """


class MailDeliveryError(MailError):
    """Mail is configured but the relay refused or could not be reached."""


def is_valid_address(value: object) -> bool:
    """Return whether *value* is an address this service will send to.

    Args:
        value: Candidate address, of unknown type.

    Returns:
        True when the value is a plain, uncommented ``local@domain`` address
        within :data:`MAX_ADDRESS_LENGTH`.
    """
    if not isinstance(value, str) or not value or len(value) > MAX_ADDRESS_LENGTH:
        return False
    if any(ch in value for ch in "\r\n\x00"):
        return False
    # `parseaddr` would happily extract an address from "Name <a@b.c>" or from
    # a comment, which is precisely the leniency the caller should not get.
    name, address = parseaddr(value)
    if name or value != address:
        return False
    return bool(_ADDRESS_RE.match(value))


def _cfg(key: str, default: object = None) -> object:
    """Read one mail setting through the instance-settings-first chain.

    Uses :class:`ConfigService` so an operator can set these from the admin UI
    without a redeploy, matching every other integration credential in the
    project.  ``MAIL_PASSWORD`` is one of the keys ``InstanceSettings``
    Fernet-encrypts at rest.

    Args:
        key: The setting name.
        default: Value to fall back to.

    Returns:
        The configured value, or *default*.
    """
    from app.core.config_service import ConfigService

    return ConfigService.get(key, default)


def _cfg_bool(key: str, default: bool) -> bool:
    """Read a boolean mail setting.

    Args:
        key: The setting name.
        default: Value when unset or unparseable.

    Returns:
        The parsed boolean.
    """
    from app.core.config_service import ConfigService

    return bool(ConfigService.get_bool(key, default))


def _cfg_int(key: str, default: int) -> int:
    """Read an integer mail setting, falling back rather than raising.

    Args:
        key: The setting name.
        default: Value when unset or unparseable.

    Returns:
        The parsed integer, or *default*.
    """
    raw = _cfg(key, None)
    try:
        return int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class MailSettings:
    """A validated, resolved mail configuration.

    Resolving and validating are separate steps on purpose: a malformed value
    must fail here, at the boundary, rather than deep inside a send where the
    stack trace points somewhere unhelpful.

    Attributes:
        host: SMTP relay hostname or IP literal.
        port: SMTP relay port.
        username: Authentication username, or None for an open relay.
        password: Authentication password, or None.
        use_tls: Negotiate STARTTLS.  Ignored when *use_ssl* is set.
        use_ssl: Implicit TLS (SMTPS, typically port 465).
        timeout: Socket and command timeout in seconds.
        sender_address: The only permitted envelope/header sender.
        sender_name: Display name paired with *sender_address*.
    """

    host: str
    port: int
    username: str | None = None
    password: str | None = None
    use_tls: bool = True
    use_ssl: bool = False
    timeout: int = DEFAULT_TIMEOUT_SECONDS
    sender_address: str = ""
    sender_name: str = "iQoQo"

    @property
    def sender_header(self) -> str:
        """Return the ``From`` header value, name and address combined."""
        if self.sender_name:
            return formataddr((self.sender_name, self.sender_address))
        return self.sender_address


def load_mail_settings() -> MailSettings | None:
    """Resolve mail configuration from the instance, or None when disabled.

    Returns:
        A validated :class:`MailSettings`, or None when mail is switched off.
        Never raises for a *misconfigured* instance -- that is the caller's
        signal to fail the send with :class:`MailConfigurationError`, which
        carries a message naming the offending key.

    Raises:
        MailConfigurationError: If mail is enabled but a value is unusable.
    """
    if not _cfg_bool("MAIL_ENABLED", False):
        return None

    host = str(_cfg("MAIL_HOST", "") or "").strip()
    if not host:
        raise MailConfigurationError("MAIL_HOST is not set; outbound mail cannot be sent")
    if not _SMTP_HOST_RE.match(host):
        raise MailConfigurationError("MAIL_HOST must be a bare hostname or IP address, not a URL or path")

    port = _cfg_int("MAIL_PORT", 465 if str(_cfg("MAIL_USE_SSL", "")).strip().lower() in {"1", "true", "yes"} else 587)
    if not 1 <= port <= 65535:
        raise MailConfigurationError("MAIL_PORT must be between 1 and 65535")

    use_ssl = _cfg_bool("MAIL_USE_SSL", False)
    use_tls = _cfg_bool("MAIL_USE_TLS", not use_ssl)
    if use_ssl and use_tls:
        raise MailConfigurationError("MAIL_USE_SSL and MAIL_USE_TLS cannot both be enabled; pick implicit TLS or STARTTLS")

    sender_address = str(_cfg("MAIL_FROM_ADDRESS", "") or "").strip()
    if not sender_address:
        raise MailConfigurationError("MAIL_FROM_ADDRESS is not set; outbound mail cannot be sent")
    if not is_valid_address(sender_address):
        raise MailConfigurationError("MAIL_FROM_ADDRESS is not a valid email address")

    timeout = _cfg_int("MAIL_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
    timeout = max(MIN_TIMEOUT_SECONDS, min(timeout, MAX_TIMEOUT_SECONDS))

    return MailSettings(
        host=host,
        port=port,
        username=(str(_cfg("MAIL_USERNAME", "") or "").strip() or None),
        password=(str(_cfg("MAIL_PASSWORD", "") or "") or None),
        use_tls=use_tls,
        use_ssl=use_ssl,
        timeout=timeout,
        sender_address=sender_address,
        sender_name=str(_cfg("MAIL_FROM_NAME", "iQoQo") or "iQoQo"),
    )


def public_origin() -> str:
    """Return the trusted public origin to build links from.

    Never derived from the request.  ``request.url_root`` reflects the ``Host``
    header, so a link built from it is whatever an attacker chose to send -- and
    on an instance that has not set the variable it would silently default to
    localhost, delivering unusable links into real mailboxes.

    Raises:
        MailConfigurationError: If no origin is configured.  Failing here is
            correct: the alternative is sending a deletion link to a domain the
            recipient does not control.
    """
    raw = str(_cfg("PUBLIC_APP_URL", "") or "").strip().rstrip("/")
    if not raw:
        raise MailConfigurationError("PUBLIC_APP_URL is not set; iQoQo will not generate account email links without a known public origin")
    if not raw.startswith("https://") and not raw.startswith("http://localhost"):
        raise MailConfigurationError("PUBLIC_APP_URL must be an https:// origin (http:// is allowed only for localhost)")
    if any(ch in raw for ch in "\r\n"):
        raise MailConfigurationError("PUBLIC_APP_URL contains control characters")
    return raw


def build_link(path: str, token: str) -> str:
    """Build an absolute link to *path* carrying *token*.

    Args:
        path: An application-relative path beginning with ``/``.
        token: The raw token, appended as a query parameter.

    Returns:
        An absolute URL under :func:`public_origin`.

    Raises:
        MailConfigurationError: If *path* is not an application-relative path.
            A relative path containing ``..`` or a scheme would let a caller
            place the token on a different host.
    """
    if not path.startswith("/") or path.startswith("//") or ".." in path:
        raise MailConfigurationError(f"Refusing to build a link for a non-application-relative path: {path!r}")
    from urllib.parse import quote

    return f"{public_origin()}{path}?token={quote(token, safe='')}"


@dataclass
class OutboundMessage:
    """One message handed to a transport.

    Attributes:
        envelope_from: SMTP MAIL FROM address.
        recipient: The single RCPT TO address.
        raw: The serialised message, ready for DATA.
    """

    envelope_from: str
    recipient: str
    raw: str


class Transport(Protocol):
    """What a mail transport must be able to do."""

    def deliver(self, message: OutboundMessage, settings: MailSettings) -> None:
        """Send *message*, or raise.

        Args:
            message: The message to send.
            settings: The connection parameters to use.

        Raises:
            MailDeliveryError: If the relay refused the message or was unreachable.
        """


class SmtpTransport:
    """Deliver over SMTP, with STARTTLS or implicit TLS."""

    def deliver(self, message: OutboundMessage, settings: MailSettings) -> None:
        """Send one message through the configured relay.

        Args:
            message: The message to send.
            settings: The connection parameters to use.

        Raises:
            MailDeliveryError: On any connection, negotiation, authentication or
                relay failure.  The underlying exception is attached as
                ``__cause__`` for the logs; the message deliberately carries
                only the class name, because an SMTP error string can echo the
                message content back.
        """
        try:
            if settings.use_ssl:
                server: smtplib.SMTP = smtplib.SMTP_SSL(settings.host, settings.port, timeout=settings.timeout, local_hostname="iqoqo")
            else:
                server = smtplib.SMTP(settings.host, settings.port, timeout=settings.timeout, local_hostname="iqoqo")
        except (OSError, smtplib.SMTPException) as exc:
            raise MailDeliveryError(f"Could not connect to the mail relay: {type(exc).__name__}") from exc

        try:
            server.ehlo()
            if settings.use_tls and not settings.use_ssl:
                # A relay that does not advertise STARTTLS while STARTTLS was
                # requested is a failed send.  Continuing in plaintext would
                # hand a mailbox-control token to the network in clear.
                if not server.has_extn("starttls"):
                    raise MailDeliveryError("The mail relay does not offer STARTTLS but STARTTLS was required")
                server.starttls()
                server.ehlo()
            if settings.username:
                server.login(settings.username, settings.password or "")
            server.sendmail(message.envelope_from, [message.recipient], message.raw)
        except (TimeoutError, smtplib.SMTPException, OSError) as exc:
            raise MailDeliveryError(f"The mail relay rejected or dropped the message: {type(exc).__name__}") from exc
        finally:
            try:
                server.quit()
            except (smtplib.SMTPException, OSError):  # pragma: no cover - best effort teardown
                pass


@dataclass
class RecordingTransport:
    """A transport that records messages instead of sending them.

    The test and end-to-end surface for mail.  It exists as a class rather than
    a monkeypatch of ``smtplib.SMTP`` so that a test asserts on the exact bytes
    that would have left the host, and so an end-to-end deployment can run with
    real endpoints against a mailbox that goes nowhere.

    Attributes:
        sent: Every message passed to :meth:`deliver`, in order.
    """

    sent: list[OutboundMessage] = field(default_factory=list)

    def deliver(self, message: OutboundMessage, settings: MailSettings) -> None:
        """Record *message* without contacting a relay.

        Args:
            message: The message that would have been sent.
            settings: Unused; accepted to satisfy :class:`Transport`.
        """
        self.sent.append(message)


class MailService:
    """Build and send a single-recipient message.

    Args:
        transport: The transport to hand finished messages to.  Defaults to
            :class:`SmtpTransport`.
    """

    def __init__(self, transport: Transport | None = None) -> None:
        self._transport: Transport = transport or SmtpTransport()

    def send(
        self,
        *,
        recipient: str,
        subject: str,
        body_text: str,
        body_html: str | None = None,
    ) -> None:
        """Send one message to *recipient*.

        Args:
            recipient: The destination address.  Validated here, so a caller
                cannot reach ``sendmail`` with something unchecked.
            subject: Subject line.
            body_text: ``text/plain`` body.
            body_html: Optional ``text/html`` alternative.

        Raises:
            MailConfigurationError: If mail is disabled, unconfigured, or the
                recipient is invalid.  Carries which of those it was.
            MailDeliveryError: If the relay refused or was unreachable.
        """
        if not is_valid_address(recipient):
            raise MailConfigurationError("Refusing to send to an address that failed validation")

        settings = load_mail_settings()
        if settings is None:
            raise MailConfigurationError("Outbound mail is disabled (MAIL_ENABLED is not set); this instance cannot send account email")

        message = self._build(recipient=recipient, subject=subject, body_text=body_text, body_html=body_html, settings=settings)
        self._transport.deliver(message, settings)
        logger.info("Sent %s message to %s via %s", "multipart" if body_html else "text", _mask(recipient), settings.host)

    def _build(
        self,
        *,
        recipient: str,
        subject: str,
        body_text: str,
        body_html: str | None,
        settings: MailSettings,
    ) -> OutboundMessage:
        """Assemble the message.

        Every header is set from a validated value or from configuration.
        ``EmailMessage`` rejects a header containing a newline outright, and the
        recipient was shape-checked before this point, so header injection has
        no path here.
        """
        msg = EmailMessage()
        msg["From"] = settings.sender_header
        msg["To"] = recipient
        msg["Subject"] = subject
        msg["Date"] = formatdate(localtime=False, usegmt=True)
        msg["Message-ID"] = make_msgid(domain=settings.sender_address.rpartition("@")[2] or None)
        msg.set_content(body_text)
        if body_html:
            msg.add_alternative(body_html, subtype="html")

        return OutboundMessage(
            envelope_from=settings.sender_address,
            recipient=recipient,
            raw=msg.as_string(policy=msg.policy.clone(linesep="\r\n")),
        )


def _mask(address: str) -> str:
    """Return *address* with most of the local part removed.

    Mailbox addresses appear in application logs routinely, and they are
    personal data.  The domain is kept because it is the part an operator
    actually needs to debug a relay problem.

    Args:
        address: The address to mask.

    Returns:
        The masked form, e.g. ``a***z@example.com``.
    """
    local, sep, domain = address.partition("@")
    if not sep:
        return "***"
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    return f"{local[0]}***{local[-1]}@{domain}"


_service: MailService | None = None


def get_mail_service() -> MailService:
    """Return the process-wide :class:`MailService`.

    A singleton so the transport choice is made once per process rather than
    per send.  ``MAIL_TRANSPORT=memory`` swaps in a :class:`RecordingTransport`,
    which is how the end-to-end stack exercises the real endpoints, including
    the confirmation link, without a relay or a live mailbox.

    Returns:
        The shared service.
    """
    global _service  # noqa: PLW0603  # pylint: disable=global-statement
    if _service is None:
        transport: Transport = RecordingTransport() if _cfg("MAIL_TRANSPORT", "smtp") == "memory" else SmtpTransport()
        _service = MailService(transport=transport)
    return _service


def set_mail_service(service: MailService | None) -> None:
    """Replace or clear the process-wide service.

    For tests and for the end-to-end stack, which run with
    ``MAIL_TRANSPORT=memory`` and need the recorded messages.

    Args:
        service: The service to install, or None to restore the default.
    """
    global _service  # noqa: PLW0603  # pylint: disable=global-statement
    _service = service

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
"""The four transactional emails the account lifecycle sends.

Kept apart from the transport in :mod:`app.core.mail_service` so that what is
said to a user can be reviewed without reading any SMTP code, and so the
wording is testable as text.

Two rules hold across every template here:

**Say what has not happened yet.**  The deletion request mail must state
explicitly that nothing has been deleted and that confirmation is required.
A "confirm your account deletion" mail that does not say so is a well-worn
phishing pattern, and a user who has genuinely asked to leave should still be
able to tell this apart from one.

**Say what to do if it was not them.**  Every mail carries an explicit
"if you did not request this, ignore it" line.  A single-use link that an
attacker mailed to a victim is inert without the victim's session, but silence
in that situation is what turns a harmless mail into a support incident.

No template embeds anything about the account beyond the display name, and the
completion mail carries no link and no token at all -- by the time it is sent
the token is spent, and a spent token in a mailbox is a link-shaped hazard for
whichever human reads it next.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Signature-appended marker, so a mail filtering rule can find these and an
#: end user can tell where they came from.  Deliberately plain text.
FOOTER = "This is an automated message from your iQoQo instance. Do not reply to it."


@dataclass(frozen=True)
class RenderedMail:
    """A rendered message, ready to hand to :class:`~app.core.mail_service.MailService`.

    Attributes:
        subject: Subject line.
        text: ``text/plain`` body.
    """

    subject: str
    text: str


def email_verification(display_name: str | None, link: str) -> RenderedMail:
    """Render the "confirm this address" mail.

    Args:
        display_name: The account's display name, or None.
        link: The verification URL.

    Returns:
        The rendered message.
    """
    greeting = f"Hello {display_name}," if display_name else "Hello,"
    text = f"""{greeting}

Confirm this email address for your iQoQo account.

{link}

The link is valid for 24 hours and can be used once. If it has expired, request
a new one from Profile -> Email verification.

Until you confirm the address, your account is not able to use the features
that require a verified mailbox.

If you did not request this, you can ignore this message. Nothing has changed
on your account.

{FOOTER}"""
    return RenderedMail(
        subject="Confirm your iQoQo email address",
        text=text,
    )


def email_verification_failed(reason: str) -> RenderedMail:
    """Render the notice for a verification link that no longer works.

    Sent to the address on the account so the owner learns the link is dead
    even if they opened it on the wrong device.  It carries no token and no
    link -- the recipient can request a fresh one themselves.

    Args:
        reason: A short, non-secret explanation. One of ``expired``,
            ``already_used``, ``address_changed`` or ``invalid``.

    Returns:
        The rendered message.
    """
    explanations = {
        "expired": "The confirmation link has expired. Links are valid for 24 hours.",
        "already_used": "That confirmation link has already been used. Each link works only once.",
        "address_changed": "The account's email address changed after that link was sent, so it no longer applies.",
        "invalid": "That confirmation link is not valid.",
    }
    text = f"""{explanations.get(reason, explanations["invalid"])}

Request a new link from Profile -> Email verification.

No action was taken on your account, and its email address is unchanged.

{FOOTER}"""
    return RenderedMail(
        subject="Your iQoQo email confirmation link is no longer valid",
        text=text,
    )


def deletion_requested(display_name: str | None, link: str, expires_in_minutes: int) -> RenderedMail:
    """Render the "a deletion is waiting for you" mail.

    States up front that nothing has been deleted.  The recipient has to be
    able to tell, from this mail alone, that their account is still intact --
    because if they requested it, that is the reassurance they need, and if
    they did not, it is the warning that stops them clicking.

    Args:
        display_name: The account's display name, or None.
        link: The confirmation URL.
        expires_in_minutes: How long the link stays valid.

    Returns:
        The rendered message.
    """
    greeting = f"Hello {display_name}," if display_name else "Hello,"
    text = f"""{greeting}

A request to permanently delete your iQoQo account is waiting for you to
confirm.

Nothing has been deleted. Your account, your library and your data are
untouched until you confirm, and you can ignore this message and do nothing at
any time.

To confirm the deletion, sign in to the account on the same device you are
reading this on, then open this link:

{link}

The link can be used once, expires in {expires_in_minutes} minutes, and only
works while you are signed in to the account it belongs to.

Deleting your account is permanent. Your profile, your library, your notes and
your lending history are all removed and cannot be recovered. There is no grace
period after you confirm.

If you did not request this, ignore this message and nothing will happen. You
can also request a fresh link at any time, which invalidates this one.

{FOOTER}"""
    return RenderedMail(
        subject="Confirm permanent deletion of your iQoQo account",
        text=text,
    )


def deletion_completed(display_name: str | None) -> RenderedMail:
    """Render the notice sent after the account is gone.

    Carries no link and no token.  It exists so the owner has a record that
    the request went through, and because a request they may have asked someone
    else to make deserves an answer.

    Args:
        display_name: The account's display name, or None.

    Returns:
        The rendered message.
    """
    greeting = f"Hello {display_name}," if display_name else "Hello,"
    text = f"""{greeting}

Your iQoQo account has been deleted.

The deletion completed at your confirmation. Your profile, library, notes and
lending history were removed and cannot be recovered.

Any other session on that account is signed out and can no longer be used.

If you did not confirm this, reply to your instance administrator: it means
someone with access to your mailbox and your session completed the deletion.

{FOOTER}"""
    return RenderedMail(
        subject="Your iQoQo account has been deleted",
        text=text,
    )

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
"""The HTML pages served from an emailed account link.

Rendered here, by the API, rather than by the Next.js frontend. That keeps the
security properties structural instead of aspirational:

**No third-party resource can be requested.** An inline stylesheet, no script,
no font, no remote image, and a ``Content-Security-Policy`` of ``default-src
'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none';
frame-ancestors 'none'`` that enforces it. A future edit that adds a script or
an analytics pixel breaks the page loudly instead of quietly phoning home.
``frame-ancestors 'none'`` matters for the same reason -- these pages are a
clickjacking target, since being framed turns "confirm" into "confirm what the
attacker behind the frame says".

**No referrer can leak the token.** The token arrives in the query string, so any
subresource or outbound link would carry it. With ``no-referrer`` and no
subresource there is nothing left to leak it, and the header is set on the
response rather than only in a meta tag.

**The page cannot act.** Everything is a ``GET`` that renders, plus a form that
``POST``s. A mail scanner or prefetcher produces byte-identical behaviour to a
human. That is the whole reason the irreversible operation lives behind the POST.

**It looks like iQoQo.** This one is a security property, not decoration. An
email link leading to an unbranded page is indistinguishable from a phishing
page, and a user who cannot tell where they are will reasonably distrust the
real thing. So the wordmark, the palette, and the favicon are all inlined --
zero network requests, but unmistakably this product. The colours are taken from
``frontend/app/globals.css`` so the two cannot drift apart in appearance.
"""

from __future__ import annotations

from html import escape

from flask import Response

#: Sent on every page this module renders.  ``no-store`` so a shared machine, a
#: proxy cache, or the back button cannot replay a page containing a live token.
_NO_STORE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, private",
    "Pragma": "no-cache",
    "Expires": "0",
    "Referrer-Policy": "no-referrer",
    "X-Robots-Tag": "noindex, nofollow, noarchive",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    # No script, no connect, no image, no font, no frame: the page can only draw
    # itself and post a form back to this origin. `frame-ancestors 'none'` is
    # what makes the page un-frameable.
    #
    # `data:` is permitted for images solely so the favicon can be an inline SVG
    # rather than a request. It cannot be used to exfiltrate anything: there is
    # no script and no form action outside `'self'`.
    #
    # `sandbox` is deliberately *not* used. A sandboxed document gets an opaque
    # origin, which makes the `form-action 'self'` source expression fail to
    # match -- silently disabling the very form this page exists to submit.
    "Content-Security-Policy": (
        "default-src 'none'; style-src 'unsafe-inline'; img-src data:; form-action 'self'; " "base-uri 'none'; frame-ancestors 'none'"
    ),
}

#: Inline favicon, so even the tab carries the product mark. A ``data:`` URI, so
#: it costs no request. Deliberately simple rather than the real logo asset: it
#: has to survive being written inside an HTML attribute.
_FAVICON = (
    "data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
    "%3Crect width='32' height='32' rx='7' fill='%23334352'/%3E"
    "%3Ctext x='16' y='22' font-family='Helvetica,Arial,sans-serif' font-size='15' "
    "font-weight='700' fill='%23fbf7ef' text-anchor='middle'%3Ei%3C/text%3E%3C/svg%3E"
)

#: Palette mirrored from `frontend/app/globals.css` (HSL, light and dark).
_BRAND_INK = "hsl(210 29% 24%)"
_BRAND_PAPER = "hsl(43 50% 98%)"
_BRAND_DARK_INK = "hsl(43 50% 90%)"
_BRAND_DARK_PAPER = "hsl(210 11% 15%)"
_BRAND_MUTED = "hsl(210 12% 45%)"

# Inline and minimal. A stylesheet is the one thing a CSP still has to permit,
# and inlining it is what lets the policy drop `style-src` down to a single value
# with no host to point at.
#
# Written one rule per line and brace-balanced. An earlier revision was missing
# a closing brace after the dark-mode `body` rule, which nested `.card` inside
# the `prefers-color-scheme: dark` query: the card was styled in dark mode and
# completely unstyled in light mode. It survived because the pages were checked
# with `curl`, which never renders, and because the dark path happened to work.
_STYLE = f"""
:root {{ color-scheme: light dark; }}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; padding: 2.5rem 1rem; background: {_BRAND_PAPER}; color: {_BRAND_INK};
  font: 16px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}}
.wrap {{ max-width: 32rem; margin: 0 auto; }}
.brand {{ display: flex; align-items: center; gap: .5rem; margin-bottom: 1rem; }}
.brand b {{ font-size: 1.05rem; letter-spacing: -.01em; color: {_BRAND_INK}; }}
.card {{
  background: #fff; border: 1px solid hsl(210 12% 88%); border-radius: 12px;
  padding: 2rem; box-shadow: 0 1px 2px hsl(210 29% 24% / .06);
}}
h1 {{ font-size: 1.35rem; margin: 0 0 1rem; line-height: 1.3; }}
p {{ margin: 0 0 1rem; }}
.muted {{ color: {_BRAND_MUTED}; font-size: .9rem; }}
.danger {{
  border: 1px solid #dc2626; background: #fef2f2; color: #7f1d1d;
  border-radius: 8px; padding: .85rem 1rem; font-size: .9rem; margin: 0 0 1.25rem;
}}
button {{
  font: inherit; width: 100%; padding: .7rem 1rem; border-radius: 8px;
  border: 1px solid transparent; cursor: pointer; font-weight: 600;
}}
.go {{ background: {_BRAND_INK}; color: {_BRAND_PAPER}; }}
.go:hover {{ opacity: .9; }}
.go:focus-visible {{ outline: 2px solid #2563eb; outline-offset: 2px; }}
.cancel {{ display: block; margin-top: 1rem; text-align: center; font-size: .9rem; color: {_BRAND_MUTED}; }}
hr {{ border: 0; border-top: 1px solid hsl(210 12% 88%); margin: 1.5rem 0; }}
@media (prefers-color-scheme: dark) {{
  body {{ background: {_BRAND_DARK_PAPER}; color: {_BRAND_DARK_INK}; }}
  .brand b {{ color: {_BRAND_DARK_INK}; }}
  .card {{ background: hsl(210 11% 19%); border-color: hsl(210 11% 28%); box-shadow: none; }}
  .muted, .cancel {{ color: hsl(210 12% 65%); }}
  .danger {{ border-color: #7f1d1d; background: #2a1414; color: #fecaca; }}
  .go {{ background: hsl(210 29% 80%); color: hsl(210 29% 24%); }}
  hr {{ border-color: hsl(210 11% 28%); }}
}}
"""


def _page(*, title: str, body: str, status: int = 200) -> Response:
    """Wrap *body* in the page shell and return it as an HTTP response.

    Args:
        title: Document title, escaped.
        body: Already-escaped HTML for the card's contents.
        status: HTTP status.  Defaults to 200, and callers should think hard
            before changing it: a ``GET`` of an unusable link renders 200 on
            purpose (see :func:`invalid_link_page`), while a failed ``POST``
            should report its failure.

    Returns:
        A ``text/html`` response carrying the no-store, no-referrer and CSP
        headers.
    """
    document = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<meta name="robots" content="noindex, nofollow">
<title>{escape(title)}</title>
<link rel="icon" href="{_FAVICON}">
<style>{_STYLE}</style>
</head>
<body>
<div class="wrap">
<div class="brand"><b>iQoQo</b></div>
<main class="card">
{body}
</main>
</div>
</body>
</html>"""
    return Response(document, status=status, mimetype="text/html; charset=utf-8", headers=_NO_STORE_HEADERS)


def email_verification_page(*, account_hint: str, csrf_field: str = "") -> Response:
    """Render the "confirm this address" page.

    Args:
        account_hint: A short, already-safe description of the address being
            confirmed, so the user can tell at a glance whether they are in the
            right mailbox.  Only ever the address already stored on the account.
        csrf_field: A pre-rendered hidden CSRF input, or empty.  Empty means the
            caller is not relying on cookie authentication, in which case there
            is nothing to prove.

    Returns:
        The confirmation page, or a "this link is no longer valid" page when
        *csrf_field* is present but the token is not -- see
        :func:`invalid_link_page`.
    """
    body = f"""
<h1>Confirm your email address</h1>
<p>You are confirming <strong>{escape(account_hint)}</strong> as the address for your iQoQo account.</p>
<p class="muted">Confirming shows that you can receive mail at this address. It does not sign you in and does not change anything else.</p>
<form method="post" action="">
{csrf_field}
<button class="go" type="submit">Confirm this address</button>
</form>
<p class="cancel">This link can be used once, and expires in 24 hours.</p>
"""
    return _page(title="Confirm your email address", body=body)


def deletion_confirmation_page(*, account_hint: str, csrf_field: str) -> Response:
    """Render the "this deletes everything, permanently" page.

    The wording is deliberately blunt and repeated.  This page asks for the one
    action in the product that cannot be undone and cannot be recovered by the
    owner, and the person reading it may have been sent here by someone else.

    Args:
        account_hint: A short description of the account, so the user can tell
            whether they are about to delete the right thing.
        csrf_field: A pre-rendered hidden CSRF input.

    Returns:
        The confirmation page.
    """
    body = f"""
<h1>Permanently delete your account</h1>
<div class="danger">
This cannot be undone. Deleting <strong>{escape(account_hint)}</strong> permanently removes
your profile, your library, your notes, your collections and your lending history.
There is no grace period and no recovery.
</div>
<p>To confirm, you will be signed out everywhere and this link will stop working.</p>
<form method="post" action="">
{csrf_field}
<button class="go" type="submit">Yes, permanently delete my account</button>
</form>
<p class="cancel">This link expires in 30 minutes and works only once.<br>
If you did not request this, close this page -- nothing has happened.</p>
<hr>
<p class="muted">Email confirmation proves you can receive mail at this address. It is not a second sign-in, and it is not treated as one.</p>
"""
    return _page(title="Permanently delete your account", body=body)


def invalid_link_page(*, action: str) -> Response:
    """Render the "that link is not usable" page.

    One page for every rejection -- unknown, expired, already used, superseded,
    wrong account.  Distinguishing them would tell an attacker holding a token
    they cannot read how far they got, and would tell a legitimate user nothing
    actionable, because in every case the next step is identical: ask for a new
    link.

    Args:
        action: Either ``"verify"`` or ``"delete"``, selecting the copy.

    Returns:
        The page, with HTTP 200 -- see :func:`_page` for why not 404.
    """
    if action == "verify":
        heading = "This confirmation link is no longer valid"
        detail = (
            "It may have expired, already been used, or been replaced by a newer request. "
            "Request a new one from your profile under <strong>Email verification</strong>."
        )
    else:
        heading = "This deletion link is no longer valid"
        detail = (
            "It may have expired, already been used, or been replaced by a newer request. "
            "Nothing has been deleted. You can request a new link from your profile, or close this page."
        )
    body = f"""
<h1>{escape(heading)}</h1>
<p>{detail}</p>
<p class="muted">If you did not request this, no action is needed and nothing has changed on your account.</p>
"""
    return _page(title=heading, body=body)


def expired_form_page(*, detail: str) -> Response:
    """Render a CSRF rejection as a page the user can act on.

    Status 403 rather than 200. The page is the user-facing half of the
    rejection, but a form that failed its CSRF check *has* failed, and returning
    200 would let a monitoring probe -- or an E2E assertion -- read a successful
    submission. The body still says what happened and what to do, because the
    caller is a browser at a form target and a bare status code helps nobody.

    Args:
        detail: Human-readable explanation.

    Returns:
        A 403 HTML response carrying the same hardened headers as every other
        page in this flow.
    """
    return _page(
        title="This page has expired",
        body=f"<h1>This page has expired</h1><p>{escape(detail)}</p>",
        status=403,
    )


def success_page(*, heading: str, detail: str) -> Response:
    """Render a terminal outcome page.

    Args:
        heading: The outcome headline.
        detail: Explanation.  Escaped here rather than at each call site, because
            the callers pass text that carries user-controlled values -- a
            display name, an address.

    Returns:
        The page.
    """
    body = f"""
<h1>{escape(heading)}</h1>
<p>{detail}</p>
"""
    return _page(title=heading, body=body)


def sign_in_page(*, next_path: str) -> Response:
    """Render "you need to be signed in" for an otherwise-valid link.

    Reached when the token is good but the request is anonymous.  Keeping the
    link on the page and sending the user to sign in is the difference between a
    usable flow and a dead end: the token survives a login, and the sign-in page
    must therefore come back to this exact URL.

    The path is emitted into an attribute, so it is escaped.  It is built by
    this module from a fixed prefix and a fixed token length rather than taken
    from the request, so it cannot carry an attacker-chosen scheme or host.

    Args:
        next_path: The application-relative path to return to after sign-in.

    Returns:
        The page.
    """
    body = f"""
<h1>Sign in to continue</h1>
<p>This link works only for the account it was sent to. Sign in as that account, then open the link again.</p>
<p class="muted">Your session on another account is not enough -- the link is bound to one account.</p>
<form method="get" action="/login">
<input type="hidden" name="next" value="{escape(next_path, quote=True)}">
<button class="go" type="submit">Go to sign in</button>
</form>
"""
    return _page(title="Sign in to continue", body=body)

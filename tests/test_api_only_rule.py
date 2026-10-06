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
"""Enforces the "Flask Is API-Only" project rule.

The rule lives in `.agents/rules/iqoqo-standards.md`. Rules an agent cannot
violate by accident are worth more than rules only written down: the account
email-confirmation pages were built in Flask with a hand-written stylesheet,
arriving by email with no navbar or footer -- indistinguishable from a phishing
page. That is a security failure, and it happened because nothing in the build
objected.

So this asserts the boundary structurally.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = REPO_ROOT / "app"

#: Patterns that would mean the backend renders a document. Each is matched
#: against the source of every module under `app/`.
_PRESENTATION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("an explicit text/html response", re.compile(r"""mimetype\s*=\s*["']text/html""", re.IGNORECASE)),
    ("a Jinja template render", re.compile(r"\brender_template\s*\(")),
    ("an inline HTML document", re.compile(r"<!DOCTYPE html", re.IGNORECASE)),
    ("an inline <style> block", re.compile(r"<style>", re.IGNORECASE)),
    ("an inline <script> block", re.compile(r"<script", re.IGNORECASE)),
    ("a Flask Response holding markup", re.compile(r"""Response\(\s*f?["']\s*<""", re.IGNORECASE)),
)


def _python_sources() -> list[Path]:
    """Every Python module under `app/`.

    Returns:
        Sorted paths, so a failure names files deterministically.
    """
    return sorted(p for p in APP_DIR.rglob("*.py") if "__pycache__" not in p.parts)


def test_flask_renders_no_html() -> None:
    """No module under `app/` may produce an HTML document.

    The backend is JSON-only. A user-visible surface belongs to the frontend,
    which is the only layer with the design system.
    """
    offenders: list[str] = []
    for path in _python_sources():
        source = path.read_text(encoding="utf-8")
        for label, pattern in _PRESENTATION_PATTERNS:
            if pattern.search(source):
                offenders.append(f"{path.relative_to(REPO_ROOT)}: {label}")

    assert not offenders, (
        "Flask is API-only; the frontend owns presentation. Found:\n  "
        + "\n  ".join(offenders)
        + "\nRender the page as a Next.js route under frontend/app/ and expose JSON from app/."
    )


def test_the_account_flow_links_to_frontend_routes() -> None:
    """Emailed links must point at frontend routes, not API paths.

    An emailed link to `/api/...` would mean the backend was expected to render
    something, which is the thing this rule forbids.
    """
    lifecycle = (REPO_ROOT / "app" / "core" / "account_lifecycle.py").read_text(encoding="utf-8")

    paths = dict(re.findall(r'^(EMAIL_VERIFICATION_PATH|DELETION_CONFIRM_PATH) = "([^"]+)"', lifecycle, re.MULTILINE))
    assert set(paths) == {"EMAIL_VERIFICATION_PATH", "DELETION_CONFIRM_PATH"}, "link constants are missing"

    for name, path in paths.items():
        assert not path.startswith("/api/"), f"{name} points at an API path ({path}); the frontend must render it"
        assert path.startswith("/"), f"{name} must be an application-relative path ({path})"


def test_the_project_rule_is_documented() -> None:
    """The rule must exist in the agent rules file, not only in this test.

    `.github/copilot.md` is a symlink to this file, so editing it covers Copilot,
    Antigravity and anything else reading either path.
    """
    rules = (REPO_ROOT / ".agents" / "rules" / "iqoqo-standards.md").read_text(encoding="utf-8")

    assert "Flask Is API-Only" in rules, "the rule has been removed from .agents/rules/iqoqo-standards.md"
    # The security rationale matters: without it the rule reads as a style
    # preference and gets relaxed the first time it is inconvenient.
    assert "phishing" in rules, "the rule must record why it exists"

"""Invariants for `.gitleaks.toml`.

The secret scanner is only worth running if its allowlist stays narrow. These
tests exist because the obvious way to make a red Secret Scanning job green --
exempt the directory the findings are in -- also silences the scanner for every
credential ever added to that directory afterwards.

One exemption already existed and was removed: `openspec/.*` covered the entire
OpenSpec tree. See `test_openspec_tree_is_not_path_allowlisted`.
"""

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

import re
import tomllib
from pathlib import Path

import pytest

CONFIG = Path(__file__).resolve().parents[1] / ".gitleaks.toml"

# The three commits that recorded the OpenObserve default password (removed in
# v0.8.1, #309) inside OpenSpec prose. They are immutable, so the only way to
# stop a scan that reaches them from reporting them is to name them.
EXPECTED_HISTORICAL_COMMITS = {
    "7a4887d8922ff7c1e332041402f1a371f7cf1197",
    "8d49d21e3bad59b6026a88e5eff432486c9774cc",
    "c5dbe1e81877676f1facf98c06ec72b16ace9b10",
}


@pytest.fixture(scope="module")
def config() -> dict:
    """Parse the repository's gitleaks configuration.

    @returns: The parsed TOML document.
    """
    return tomllib.loads(CONFIG.read_text(encoding="utf-8"))


def _path_patterns(config: dict) -> list[str]:
    """Collect every `paths` pattern across all global allowlists.

    @param config: The parsed gitleaks configuration.
    @returns: The path regex patterns, in file order.
    """
    return [p for allowlist in config.get("allowlists", []) for p in allowlist.get("paths", [])]


def _commit_allowlist(config: dict) -> set[str]:
    """Collect every commit listed in a global allowlist.

    @param config: The parsed gitleaks configuration.
    @returns: The allowlisted commit SHAs.
    """
    return {c for allowlist in config.get("allowlists", []) for c in allowlist.get("commits", [])}


def test_openspec_tree_is_not_path_allowlisted(config: dict) -> None:
    """`openspec/` must stay in scope for future scans.

    A path allowlist matching `openspec/...` was removed on 2026-10-02. It
    existed to suppress 17 findings that all came from three historical commits,
    but it exempted the whole tree: a real credential pasted into a change
    proposal or a delta spec would never have been reported. The findings are
    suppressed at the commit instead.

    This test fails if a broad path exemption is reintroduced, whether as
    `openspec/.*`, `openspec/`, `(^|/)openspec/`, or any other pattern that
    matches a file under that directory.

    @param config: The parsed gitleaks configuration.
    @returns: Nothing; a matching exemption fails the test.
    """
    probes = (
        "openspec/changes/archive/proposal.md",
        "openspec/specs/monitoring-credential-hygiene/spec.md",
        "openspec/changes/fix/specs/backend/spec.md",
    )

    offenders = [pattern for pattern in _path_patterns(config) for probe in probes if re.search(pattern, probe)]

    assert not offenders, (
        "openspec/ is exempt from secret scanning via these path patterns: "
        f"{sorted(set(offenders))}. Suppress the historical findings at their "
        "commits instead, so new credentials in OpenSpec files are still caught."
    )


def test_historical_credential_commits_are_allowlisted(config: dict) -> None:
    """The three commits carrying the removed password must be suppressed.

    Redacting the current text does not help: a commit already in history cannot
    be rewritten, so any scan reaching these commits reports the literals again.

    @param config: The parsed gitleaks configuration.
    @returns: Nothing; a missing commit fails the test.
    """
    allowlisted = _commit_allowlist(config)
    missing = EXPECTED_HISTORICAL_COMMITS - allowlisted

    assert not missing, f"these commits are no longer suppressed and will fail Secret Scanning: {sorted(missing)}"


def _is_shallow_clone() -> bool:
    """Report whether this checkout has truncated history.

    The CI `test` job checks out at depth 1, so a commit from months ago is
    genuinely absent rather than merely unfindable, and there is nothing to
    assert about it there. The secret-scan job is the one configured with
    `fetch-depth: 0`, because gitleaks needs the history.

    @returns: True when the repository has no parent commits behind HEAD.
    """
    import subprocess

    probe = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"],
        cwd=CONFIG.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    if probe.returncode != 0:
        # Not a git checkout at all (an exported source tree, say). Treat that
        # as shallow so the caller skips rather than failing on a missing git.
        return True
    return probe.stdout.strip() == "true"


def test_allowlisted_commits_are_real(config: dict) -> None:
    """Every allowlisted SHA must resolve to a commit in this repository.

    A stale or typo'd SHA silently matches nothing, which looks like a fix while
    leaving the scanner reporting the very findings it was meant to suppress.

    Skipped in a shallow checkout, where the commit is absent for a reason that
    has nothing to do with whether the SHA is valid. `test_the_allowlist_is_exactly_
    the_three_known_commits` still runs there and catches a SHA mistyped in the
    config, because it compares the config against a literal in this file. What
    remains uncovered in CI is a SHA mistyped in *both* places -- accepted as a
    small price for not failing a job that cannot answer the question.

    Reachability from HEAD is deliberately *not* required. One of these commits
    (`8d49d21e`) exists only on `release/0.8.1`, so no scan on this branch can
    reach it -- but a branch cut from that release would. Pinning the set exactly
    keeps a placeholder from being added here without also being justified there.

    @param config: The parsed gitleaks configuration.
    @returns: Nothing; a nonexistent commit fails the test.
    """
    import subprocess

    if _is_shallow_clone():
        pytest.skip("history is truncated in this checkout, so old commits cannot be resolved")

    for commit in sorted(_commit_allowlist(config)):
        exists = subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            cwd=CONFIG.parent,
            capture_output=True,
            check=False,
        )
        assert exists.returncode == 0, f"allowlisted commit {commit} does not exist in this repository"


def test_the_allowlist_is_exactly_the_three_known_commits(config: dict) -> None:
    """The commit allowlist must not grow without justification.

    An allowlist entry is a permanent, silent exemption. Pinning the set means
    adding a fourth requires editing this test, where the reason has to be
    written down.

    @param config: The parsed gitleaks configuration.
    @returns: Nothing; an unexpected commit fails the test.
    """
    assert _commit_allowlist(config) == EXPECTED_HISTORICAL_COMMITS, (
        "the commit allowlist must contain exactly the three commits that recorded "
        "the removed OpenObserve password. Every addition is a standing exemption "
        "from secret scanning and needs its own justification."
    )


def test_removed_default_password_rule_is_still_exact(config: dict) -> None:
    """The OpenObserve rule must keep matching only the removed literal.

    The rule once read a case-insensitive alternation of two things: the exact
    default password, and the bare word `supersecret`. That second arm matched
    any case variant of that word anywhere in the repository -- prose in
    docs/MONITORING.md, the `ghp_superSecretToken12345` fixture in
    tests/test_models.py, and the redaction fixture -- accounting for 60 of 111
    historical findings while being capable of detecting nothing real, because
    the password it was written to catch no longer exists. A rule that cries wolf
    trains reviewers to ignore the scanner, and to suppress whatever it reports
    next, including a genuine leak.

    The literal is assembled from fragments rather than written out. This file
    was flagged by Secret Scanning when it contained the value verbatim: the rule
    fires on any committed occurrence, and a test that pins the rule is the last
    place one should reintroduce the string it pins. Splitting it follows the
    convention `tests/bash/sync_agy_memory.bats` already uses for its
    secret-shaped fixtures, and is stronger than an allowlist entry -- no rule can
    match a line that holds no complete value.

    @param config: The parsed gitleaks configuration.
    @returns: Nothing; a broadened regex fails the test.
    """
    removed_default = "Super" + "Secret!" + "123"

    rules = {rule["id"]: rule for rule in config.get("rules", [])}

    assert "iqoqo-openobserve-hardcoded-password" in rules, "the exact-literal regression guard was removed"

    regex = rules["iqoqo-openobserve-hardcoded-password"]["regex"]
    assert regex == removed_default, (
        f"the OpenObserve password rule must match the removed literal exactly, got {regex!r}. "
        "Broadening it re-creates the false-positive flood that rule was narrowed to stop."
    )


def test_env_file_patterns_still_present(config: dict) -> None:
    """Untracked local env files must stay exempt from path scanning.

    A `gitleaks dir` run on a developer machine would otherwise print real
    credentials from `.env` into the terminal and into CI logs -- the opposite of
    what the rule is for. These files are git-ignored, so the entry costs a
    history scan nothing.

    @param config: The parsed gitleaks configuration.
    @returns: Nothing; a missing env-file pattern fails the test.
    """
    patterns = _path_patterns(config)
    for expected in (r"(^|/)\.env$", r"(^|/)\.env\.prod$"):
        assert expected in patterns, f"{expected} is no longer allowlisted; .env scans would echo live credentials"

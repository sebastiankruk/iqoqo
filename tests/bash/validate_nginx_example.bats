#!/usr/bin/env bats
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
# Tests for scripts/validate_nginx_example.py, which guards
# deploy/nginx.conf.example (OpenSpec §2.1-§2.3).
#
# The validator's own value depends on it failing when it should. Most of these
# tests corrupt a *copy* of the config and assert the validator rejects it -- a
# validator that passes everything is worse than none, because it launders an
# unvalidated reference config as a validated one.
#
# The copy matters. An earlier version of this file mutated the real
# deploy/nginx.conf.example in place and restored it in teardown, which meant
# that an interrupted run left the committed config corrupted for every
# subsequent test in the file. Tests here never write to the repository.

setup() {
  export REPO_ROOT="${BATS_TEST_DIRNAME}/../.."
  export VALIDATOR="${REPO_ROOT}/scripts/validate_nginx_example.py"
  export COMMITTED="${REPO_ROOT}/deploy/nginx.conf.example"

  # Each test gets its own scratch copy.
  WORK_DIR="$(mktemp -d)"
  export CONFIG="${WORK_DIR}/nginx.conf.example"
  cp "${COMMITTED}" "${CONFIG}"

  # A structural-only run: no docker, no nginx. Fast, and sufficient for the
  # presence and placement assertions.
  run_validator() {
    python3 "${VALIDATOR}" --no-docker --config "${CONFIG}"
  }
}

teardown() {
  [ -n "${WORK_DIR:-}" ] && rm -rf "${WORK_DIR}"
}

# Corrupt the scratch copy in a specific way. Kept as named cases so a failure
# names the defect rather than a line number in a heredoc.
mutate() {
  CONFIG="${CONFIG}" python3 - "$1" <<'PY'
import os
import sys
from pathlib import Path

config = Path(os.environ["CONFIG"])
text = config.read_text()
op = sys.argv[1]

MUTATIONS = {
    # A commented-out header parses cleanly and loses the header: only the
    # presence check can catch it.
    "drop_hsts": lambda t: t.replace('    add_header Strict-Transport-Security "max-age=31536000" always;\n', ""),
    "comment_csp": lambda t: t.replace('    add_header Content-Security-Policy "', '    # add_header Content-Security-Policy "'),
    "drop_scanner_zone": lambda t: t.replace("limit_req_zone $binary_remote_addr zone=api_scanner:10m  rate=5r/s;\n", ""),
    "downgrade_immutable": lambda t: t.replace(
        'add_header Cache-Control "public, max-age=31536000, immutable" always;',
        'add_header Cache-Control "public" always;',
    ),
    "server_tokens_on": lambda t: t.replace("    server_tokens off;\n", ""),
    "unknown_placeholder": lambda t: t.replace("${SERVER_NAME}", "${NOT_A_REAL_PLACEHOLDER}"),
    # A stray brace in a comment must not affect brace balance.
    "braces_in_comment": lambda t: t.replace("# OpenSpec change", "# a stray } brace in a comment\n# OpenSpec change"),
    # `upstream` is http-context only; inside `server` nginx rejects it. This is
    # the structural mistake most likely to be reintroduced by an edit.
    "upstream_in_server": lambda t: t.replace(
        "upstream iqoqo_api {\n    zone iqoqo_api 64k;\n    resolver 127.0.0.11 valid=30s ipv6=off;\n"
        "    server ${API_UPSTREAM}:${API_PORT} resolve;\n}\n",
        "",
    ).replace("    # ── Proxy preamble", (
        "    upstream iqoqo_api {\n        zone iqoqo_api 64k;\n"
        "        resolver 127.0.0.11 valid=30s ipv6=off;\n"
        "        server ${API_UPSTREAM}:${API_PORT} resolve;\n    }\n\n"
        "    # ── Proxy preamble"
    ), 1),
    "extra_brace": lambda t: t.rstrip() + "\n}\n",
}

config.write_text(MUTATIONS[op](text))
PY
}

@test "the example config exists and is non-empty" {
  [ -s "${COMMITTED}" ]
}

@test "the committed config passes structural validation" {
  # Validates the file as committed, via the default path, so this also covers
  # the default-argument wiring. The validator's own output is echoed on
  # failure: a bare status assertion hides the reason.
  run python3 "${VALIDATOR}" --no-docker
  if [ "${status}" -ne 0 ]; then
    echo "validator said:" >&2
    echo "${output}" >&2
  fi
  [ "${status}" -eq 0 ]
  [[ "${output}" =~ "[OK]  structure" ]]
}

@test "the committed config validates against a real nginx" {
  if ! command -v nginx >/dev/null 2>&1 && ! command -v docker >/dev/null 2>&1; then
    skip "neither nginx nor docker available for a parse check"
  fi
  run python3 "${VALIDATOR}"
  [ "${status}" -eq 0 ]
  [[ "${output}" =~ "is a valid nginx configuration" ]]
}

@test "validation fails when HSTS is removed" {
  mutate drop_hsts
  run run_validator
  [ "${status}" -ne 0 ]
  [[ "${output}" =~ "HSTS" ]]
}

@test "validation fails when the CSP is commented out" {
  mutate comment_csp
  run run_validator
  [ "${status}" -ne 0 ]
  [[ "${output}" =~ "CSP" ]]
}

@test "validation fails when the api_scanner rate limit zone is removed" {
  mutate drop_scanner_zone
  run run_validator
  [ "${status}" -ne 0 ]
  [[ "${output}" =~ "api_scanner" ]]
}

@test "validation fails when immutable static caching is downgraded" {
  mutate downgrade_immutable
  run run_validator
  [ "${status}" -ne 0 ]
  [[ "${output}" =~ "immutable" ]]
}

@test "validation fails when server_tokens off is removed" {
  mutate server_tokens_on
  run run_validator
  [ "${status}" -ne 0 ]
  [[ "${output}" =~ "version suppression" ]]
}

@test "validation fails when upstream is declared inside a server block" {
  mutate upstream_in_server
  run run_validator
  [ "${status}" -ne 0 ]
  [[ "${output}" =~ "upstream" ]]
}

@test "validation fails on unbalanced braces" {
  mutate extra_brace
  run run_validator
  [ "${status}" -ne 0 ]
  [[ "${output}" =~ "unbalanced braces" ]]
}

@test "validation fails on an unknown placeholder" {
  # An unrendered placeholder would reach a real deployment and break it, so
  # the validator refuses rather than substituting a blank.
  mutate unknown_placeholder
  run run_validator
  [ "${status}" -ne 0 ]
  [[ "${output}" =~ "unknown placeholder" ]]
  [[ "${output}" =~ "NOT_A_REAL_PLACEHOLDER" ]]
}

@test "braces inside comments do not affect brace balance" {
  # The file documents itself in comments containing example directives with
  # braces. A naive counter would report a spurious imbalance, which trains
  # readers to ignore the check.
  mutate braces_in_comment
  run run_validator
  if [ "${status}" -ne 0 ]; then
    {
      echo "--- validator diagnostics ---"
      echo "python3: $(command -v python3) ($(python3 --version 2>&1))"
      echo "config: ${CONFIG}"
      echo "validator exit: ${status}"
      echo "validator output:"
      echo "${output}"
    } >&2
    false
  fi
}

@test "the mutated config still parses after a comment containing braces" {
  mutate braces_in_comment
  if ! command -v nginx >/dev/null 2>&1 && ! command -v docker >/dev/null 2>&1; then
    skip "neither nginx nor docker available for a parse check"
  fi
  run python3 "${VALIDATOR}" --config "${CONFIG}"
  [ "${status}" -eq 0 ]
}

@test "the committed config is never modified by these tests" {
  # Guards the hermeticity the rest of this file depends on. An earlier version
  # mutated the real file and restored it in teardown; an interrupted run left
  # the committed config corrupted and every later test in the file failed for
  # the wrong reason.
  run git -C "${REPO_ROOT}" diff --quiet -- deploy/nginx.conf.example
  [ "${status}" -eq 0 ]
}

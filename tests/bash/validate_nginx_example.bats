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
# tests mutate a valid config to confirm the check is not vacuously green --
# a validator that passes everything is worse than none, because it launders an
# unvalidated reference config as a validated one.

setup() {
  export EXAMPLE="${BATS_TEST_DIRNAME}/../../deploy/nginx.conf.example"
  export VALIDATOR="${BATS_TEST_DIRNAME}/../../scripts/validate_nginx_example.py"
  export BACKUP="${BATS_TEST_DIRNAME}/../../.nginx.example.bats-backup"
  cp "${EXAMPLE}" "${BACKUP}"

  # A structural-only run: no docker, no nginx. Fast, and sufficient for the
  # presence and placement assertions.
  run_validator() {
    python3 "${VALIDATOR}" --no-docker
  }
}

teardown() {
  cp "${BACKUP}" "${EXAMPLE}"
  rm -f "${BACKUP}"
}

mutate() {
  # Apply a python transformation to the example, run the validator, restore.
  python3 - "$1" <<'PY'
import sys
from pathlib import Path

example = Path("deploy/nginx.conf.example")
text = example.read_text()
op = sys.argv[1]

if op == "drop_hsts":
    text = text.replace('    add_header Strict-Transport-Security "max-age=31536000" always;\n', "")
elif op == "drop_csp":
    text = text.replace('    add_header Content-Security-Policy "', '    # add_header Content-Security-Policy "')
elif op == "drop_scanner_zone":
    text = text.replace("limit_req_zone $binary_remote_addr zone=api_scanner:10m  rate=5r/s;\n", "")
elif op == "drop_immutable":
    text = text.replace('add_header Cache-Control "public, max-age=31536000, immutable" always;', 'add_header Cache-Control "public" always;')
elif op == "upstream_in_server":
    block = "upstream iqoqo_api {\n    zone iqoqo_api 64k;\n    resolver 127.0.0.11 valid=30s ipv6=off;\n    server ${API_UPSTREAM}:${API_PORT} resolve;\n}\n"
    text = text.replace(block, "").replace("    # ── Proxy preamble", block + "\n    # ── Proxy preamble")
elif op == "extra_brace":
    text = text.rstrip() + "\n}\n"
elif op == "server_tokens_on":
    text = text.replace("    server_tokens off;\n", "")
elif op == "unknown_placeholder":
    text = text.replace("${SERVER_NAME}", "${NOT_A_REAL_PLACEHOLDER}")
elif op == "braces_in_comment":
    # The validator must ignore braces that appear inside comments.
    text = text.replace("# OpenSpec change", "# a stray } brace in a comment\n# OpenSpec change")
else:
    raise SystemExit(f"unknown mutation {op}")

example.write_text(text)
PY
}

@test "the example config exists" {
  [ -f "${EXAMPLE}" ]
}

@test "the example config passes structural validation" {
  run run_validator
  [ "$status" -eq 0 ]
  [[ "$output" =~ "[OK]  structure" ]]
}

@test "the example config validates against a real nginx" {
  # Skipped rather than failed when neither nginx nor docker is present: the
  # structural check still runs above, and failing here would make the suite
  # depend on a container runtime being installed.
  if ! command -v nginx >/dev/null 2>&1 && ! command -v docker >/dev/null 2>&1; then
    skip "neither nginx nor docker available for a parse check"
  fi
  run python3 "${VALIDATOR}"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "is a valid nginx configuration" ]]
}

@test "validation fails when HSTS is removed" {
  mutate drop_hsts
  run run_validator
  [ "$status" -ne 0 ]
  [[ "$output" =~ "HSTS" ]]
}

@test "validation fails when the CSP is commented out" {
  # A commented-out header is a silent regression: the config still parses, so
  # only the presence check catches it.
  mutate drop_csp
  run run_validator
  [ "$status" -ne 0 ]
  [[ "$output" =~ "CSP" ]]
}

@test "validation fails when the api_scanner rate limit zone is removed" {
  mutate drop_scanner_zone
  run run_validator
  [ "$status" -ne 0 ]
  [[ "$output" =~ "api_scanner" ]]
}

@test "validation fails when immutable static caching is downgraded" {
  mutate drop_immutable
  run run_validator
  [ "$status" -ne 0 ]
  [[ "$output" =~ "immutable" ]]
}

@test "validation fails when server_tokens off is removed" {
  mutate server_tokens_on
  run run_validator
  [ "$status" -ne 0 ]
  [[ "$output" =~ "version suppression" ]]
}

@test "validation fails when upstream is declared inside a server block" {
  # nginx rejects this outright, and it is the most likely structural mistake
  # to reintroduce when editing the file.
  mutate upstream_in_server
  run run_validator
  [ "$status" -ne 0 ]
  [[ "$output" =~ "upstream" ]]
}

@test "validation fails on unbalanced braces" {
  mutate extra_brace
  run run_validator
  [ "$status" -ne 0 ]
  [[ "$output" =~ "unbalanced braces" ]]
}

@test "validation fails on an unknown placeholder" {
  # An unrendered placeholder would reach a real deployment and break it, so
  # the validator refuses rather than substituting a blank.
  mutate unknown_placeholder
  run run_validator
  [ "$status" -ne 0 ]
  [[ "$output" =~ "unknown placeholder" ]]
  [[ "$output" =~ "NOT_A_REAL_PLACEHOLDER" ]]
}

@test "braces inside comments do not affect brace balance" {
  # The file documents itself in comments containing example directives with
  # braces. A naive counter would report a spurious imbalance, which trains
  # readers to ignore the check.
  mutate braces_in_comment
  run run_validator
  [ "$status" -eq 0 ]
}

@test "the example still parses after a comment containing braces is added" {
  mutate braces_in_comment
  if ! command -v nginx >/dev/null 2>&1 && ! command -v docker >/dev/null 2>&1; then
    skip "neither nginx nor docker available for a parse check"
  fi
  run python3 "${VALIDATOR}"
  [ "$status" -eq 0 ]
}

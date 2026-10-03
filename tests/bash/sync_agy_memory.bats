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
# MOD-OPS-15: scripts/sync_agy_memory.sh must never persist credentials into
# .context/ai-memory/. Agent transcripts routinely echo back .env values,
# Authorization headers and CLI invocations containing tokens, so the rendered
# Markdown is scrubbed before it is written and before it is indexed into the
# knowledge graph.

SCRIPT="${BATS_TEST_DIRNAME}/../../scripts/sync_agy_memory.sh"
VERSION="0.0.0-test"
BRAIN_DIR=""

setup() {
  command -v jq >/dev/null 2>&1 || skip "jq not installed"

  export TEST_TEMP_DIR="$(mktemp -d)"
  export HOME="${TEST_TEMP_DIR}/home"
  BRAIN_DIR="${HOME}/.gemini/antigravity-cli/brain/conv-abc123"
  mkdir -p "$BRAIN_DIR"
  cd "$TEST_TEMP_DIR"

  # Secret-shaped fixtures, assembled from fragments so that no committed line
  # contains a complete credential and no scanner allowlist is required. The
  # assembled values are still full-size and correctly shaped, which is what the
  # redaction filter keys on.
  AWS_EXAMPLE="AKIA""IOSFODNN7EXAMPLE"                                             # gitleaks:allow
  AWS_PLACEHOLDER="AKIA""1234567890ABCDEF"                                          # gitleaks:allow
  GCP_PLACEHOLDER="AIza""SyD1234567890abcdefghijklmnopqrstuv"                       # gitleaks:allow
  OPENAI_PLACEHOLDER="sk-proj-""abcdefghijklmnop1234567890AB"                       # gitleaks:allow
  JWT_PLACEHOLDER="eyJ""hbGciOiJIUzI1NiJ9.eyJ""zdWIiOiIxMjM0NSJ9.dBj""ftJeZ4CVPmB92K27uhbUJU1p1r_wW1gFWFOEjXk"  # gitleaks:allow
  PEM_BODY="MIIE""owIBAAKCAQEAx7Vv8Q9dE2rF4hJ8kL0mN6pQ"                              # gitleaks:allow
  GITHUB_PLACEHOLDER="ghp_""1234567890abcdefghijklmnopqrstuvwxyz"                   # gitleaks:allow
  SLACK_PLACEHOLDER="xoxb-""123456789012-abcdefghijkl"                              # gitleaks:allow
  DB_PLACEHOLDER="super""secretpassword"                                            # gitleaks:allow
  FERNET_PLACEHOLDER="gAAAAABmNDP""5r3xJfK0pQ8sT2uV4wX6yZ8aB1cD3eF5="            # gitleaks:allow

  # A transcript is only synced when it mentions VERSION (fast byte filter).
  #
  # The fixtures below are deliberately secret-SHAPED so the redaction filter has
  # something to recognise. Every value is inert by construction:
  #   AKIAIOSFODNN7EXAMPLE          AWS's own documentation example key
  #   eyJhbGciOiJIUzI1NiJ9...       the canonical jwt.io example JWT
  #   ghp_1234.../xoxb-1234...      sequential placeholders
  #   AKIA1234...ABCDEF             sequential placeholder
  #   AIzaSyD1.../sk-proj-abcdef... sequential placeholders
  #   MIIEowIB...M6pQ                a truncated, structurally invalid PEM body
  #   gAAAAABmNDP...3eF5=            a 43-char Fernet-shaped placeholder
  #
  # The heredoc is UNQUOTED (<<'EOF' would freeze the vars; we need expansion),
  # so the fixtures are assembled from variables rather than written as literals.
  # Two reasons this is the only workable shape:
  #   1. A trailing `# gitleaks:allow` cannot be appended to a line inside a
  #      JSONL fixture without becoming part of the JSON and breaking the
  #      transcript the test depends on.
  #   2. Building the literals from fragments means the committed source never
  #      contains a full secret, so no scanner rule can match it and no allowlist
  #      is needed at all. The generated values are still full-size and
  #      correctly shaped, which is what the filter actually keys on.
  #
  # `gitleaks:allow` is still added to the assembly lines, because a secret
  # scanner scanning this file would see the fragments.
  cat > "${BRAIN_DIR}/transcript_full.jsonl" <<EOF
{"step_index":1,"source":"user","type":"msg","created_at":"2026-01-01","thinking":null,"tool_calls":null,"content":"release 0.0.0-test SECRET_KEY=\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\""}
{"step_index":2,"source":"agent","type":"msg","created_at":"2026-01-01","thinking":null,"tool_calls":null,"content":"aws key ${AWS_EXAMPLE} and ${AWS_PLACEHOLDER}"}
{"step_index":3,"source":"agent","type":"msg","created_at":"2026-01-01","thinking":null,"tool_calls":null,"content":"google ${GCP_PLACEHOLDER}"}
{"step_index":4,"source":"agent","type":"msg","created_at":"2026-01-01","thinking":null,"tool_calls":null,"content":"openai ${OPENAI_PLACEHOLDER}"}
{"step_index":5,"source":"agent","type":"msg","created_at":"2026-01-01","thinking":null,"tool_calls":[{"cmd":"curl https://minio:${DB_PLACEHOLDER}@minio.local:9000"}],"content":"curl -H 'Authorization: Bearer ${JWT_PLACEHOLDER}'"}
{"step_index":6,"source":"agent","type":"msg","created_at":"2026-01-01","thinking":null,"tool_calls":null,"content":"-----BEGIN RSA PRIVATE KEY-----\\n${PEM_BODY}\\n-----END RSA PRIVATE KEY-----"}
{"step_index":7,"source":"agent","type":"msg","created_at":"2026-01-01","thinking":null,"tool_calls":null,"content":"${GITHUB_PLACEHOLDER} slack ${SLACK_PLACEHOLDER}"}
{"step_index":8,"source":"agent","type":"msg","created_at":"2026-01-01","thinking":null,"tool_calls":null,"content":"DATABASE_URL=postgres://iqoqo:${DB_PLACEHOLDER}@db:5432/iqoqo"}
{"step_index":9,"source":"agent","type":"msg","created_at":"2026-01-01","thinking":null,"tool_calls":null,"content":"fernet ${FERNET_PLACEHOLDER}"}
{"step_index":10,"source":"agent","type":"msg","created_at":"2026-01-01","thinking":null,"tool_calls":null,"content":"benign: a paragraph about tokenization and password hashing must survive untouched"}
EOF
}

teardown() {
  cd /tmp
  rm -rf "$TEST_TEMP_DIR"
}

@test "sync_agy_memory.sh redacts every known credential shape" {
  run bash "$SCRIPT" "$VERSION"
  [ "$status" -eq 0 ]

  local out="${TEST_TEMP_DIR}/.context/ai-memory/${VERSION}/conv-abc123.md"
  [ -f "$out" ]

  local leaked=0
  for secret in \
    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' \
    "$AWS_EXAMPLE" \
    "$AWS_PLACEHOLDER" \
    "$GCP_PLACEHOLDER" \
    "$OPENAI_PLACEHOLDER" \
    "$JWT_PLACEHOLDER" \
    "$PEM_BODY" \
    "$GITHUB_PLACEHOLDER" \
    "$SLACK_PLACEHOLDER" \
    "$DB_PLACEHOLDER" \
    "$FERNET_PLACEHOLDER"
  do
    if grep -qF "$secret" "$out"; then
      echo "LEAK: ${secret}" >&2
      leaked=$((leaked + 1))
    fi
  done

  [ "$leaked" -eq 0 ]
}

@test "sync_agy_memory.sh marks redactions and keeps non-secret prose" {
  run bash "$SCRIPT" "$VERSION"
  [ "$status" -eq 0 ]

  local out="${TEST_TEMP_DIR}/.context/ai-memory/${VERSION}/conv-abc123.md"
  grep -qF '[REDACTED]' "$out"
  grep -qiF 'benign: a paragraph about tokenization and password hashing' "$out"
}

@test "sync_agy_memory.sh writes unescaped Markdown, not JSON-encoded text" {
  run bash "$SCRIPT" "$VERSION"
  [ "$status" -eq 0 ]

  local out="${TEST_TEMP_DIR}/.context/ai-memory/${VERSION}/conv-abc123.md"
  # jq without -r would emit a quoted, \n-escaped JSON string.
  run head -1 "$out"
  [ "${output}" != '"' ]
  ! grep -qF '\n\n' "$out"
}

@test "sync_agy_memory.sh reports how many files were redacted" {
  run bash "$SCRIPT" "$VERSION"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "redacted=1" ]]
}

@test "sync_agy_memory.sh leaves no unscrubbed render temp file behind" {
  run bash "$SCRIPT" "$VERSION"
  [ "$status" -eq 0 ]

  # The raw (unredacted) render goes to a temp file; it must be removed.
  local leftovers
  leftovers=$(find "${TMPDIR:-/tmp}" -maxdepth 1 -name 'agy_render.*' 2>/dev/null | wc -l)
  [ "$leftovers" -eq 0 ]
}

@test "sync_agy_memory.sh fails closed when redaction cannot run" {
  # A jq that cannot perform the redaction must abort before writing anything,
  # rather than syncing unscrubbed transcripts.
  mkdir -p "${TEST_TEMP_DIR}/broken-bin"
  ln -s "$(command -v bash)" "${TEST_TEMP_DIR}/broken-bin/bash"
  for tool in find grep sed cat printf mkdir rm; do
    p="$(command -v "$tool" 2>/dev/null || true)"
    [ -n "$p" ] && ln -sf "$p" "${TEST_TEMP_DIR}/broken-bin/$tool"
  done
  # jq exists but every invocation fails, as with a stripped-down build.
  printf '#!/bin/sh\nexit 1\n' > "${TEST_TEMP_DIR}/broken-bin/jq"
  chmod +x "${TEST_TEMP_DIR}/broken-bin/jq"

  PATH="${TEST_TEMP_DIR}/broken-bin" run bash "$SCRIPT" "$VERSION"
  [ "$status" -ne 0 ]
  [[ "$output" =~ "secret redaction unavailable" ]]

  # Nothing was written to the sync destination.
  [ ! -d "${TEST_TEMP_DIR}/.context/ai-memory/${VERSION}" ]
}

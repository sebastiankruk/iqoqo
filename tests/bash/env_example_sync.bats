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
# along with this program.  If not, see <https://www.gnu.org/licenses/>
#

# tests/bash/env_example_sync.bats
# Validates that .env.example covers all os.getenv/os.environ variables used in app/ and scripts/

bats_require_minimum_version 1.5.0

setup() {
    EXAMPLE_FILE=".env.example"
    TEMP_GOT="$(mktemp)"
    TEMP_NEED="$(mktemp)"
}

teardown() {
    rm -f "$TEMP_GOT" "$TEMP_NEED"
}

# Extract env var uses from Python code
extract_code_vars() {
    grep -rhoPh "(?:os\.getenv|os\.environ(?:\[|\.get))\s*\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]" \
        app/ scripts/ --include='*.py' 2>/dev/null \
        | sed -E "s/.*['\"]([^'\"]+)['\"].*/\1/" \
        | sort -u
}

# Extract keys from .env.example
extract_example_keys() {
    grep -oP '^\s*\K[A-Za-z_][A-Za-z0-9_]*(?=\s*=)' "$EXAMPLE_FILE" 2>/dev/null | sort -u
}

# ── Tests ───────────────────────────────────────────────────────

@test ".env.example exists" {
  [ -f "$EXAMPLE_FILE" ]
}

@test ".env.example has no duplicate keys" {
  keys=$(extract_example_keys)
  dupes=$(echo "$keys" | sort | uniq -d)
  if [[ -n "$dupes" ]]; then
    echo "Duplicate keys found: $dupes"
    false
  fi
}

@test ".env.example covers all os.getenv / os.environ calls in code" {
  extract_code_vars > "$TEMP_NEED"
  extract_example_keys > "$TEMP_GOT"

  missing=$(comm -23 "$TEMP_NEED" "$TEMP_GOT")
  if [[ -n "$missing" ]]; then
    echo "Missing from .env.example:"
    echo "$missing"
    false
  fi
}

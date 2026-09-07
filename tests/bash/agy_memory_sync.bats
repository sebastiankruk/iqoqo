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

# tests/bash/agy_memory_sync.bats
# Tests for scripts/sync_agy_memory.sh and the memory-presync Makefile target.

setup() {
    # Fake brain dir: session that MENTIONS the version under test
    FAKE_BRAIN_MATCH="$(mktemp -d)"
    FAKE_CONV_MATCH="${FAKE_BRAIN_MATCH}/conv-abc123/.system_generated/logs"
    mkdir -p "$FAKE_CONV_MATCH"
    printf '%s\n' \
        '{"step_index":1,"source":"USER","type":"USER_INPUT","created_at":"2026-09-01T00:00:00Z","content":"Test 0.7.17 session","thinking":null,"tool_calls":null}' \
        > "${FAKE_CONV_MATCH}/transcript_full.jsonl"

    # Fake brain dir: session that does NOT mention the version under test
    FAKE_BRAIN_SKIP="$(mktemp -d)"
    FAKE_CONV_SKIP="${FAKE_BRAIN_SKIP}/conv-xyz999/.system_generated/logs"
    mkdir -p "$FAKE_CONV_SKIP"
    printf '%s\n' \
        '{"step_index":1,"source":"USER","type":"USER_INPUT","created_at":"2026-09-01T00:00:00Z","content":"Unrelated session 0.6.0","thinking":null,"tool_calls":null}' \
        > "${FAKE_CONV_SKIP}/transcript_full.jsonl"

    export FAKE_BRAIN_MATCH FAKE_BRAIN_SKIP
}

teardown() {
    rm -rf "$FAKE_BRAIN_MATCH" "$FAKE_BRAIN_SKIP"
}

# ---------------------------------------------------------------------------
# Script error-handling tests
# ---------------------------------------------------------------------------

@test "sync_agy_memory.sh: exits 1 with no VERSION argument" {
    run bash scripts/sync_agy_memory.sh
    [ "$status" -eq 1 ]
    [[ "$output" == *"Usage"* ]]
}

# ---------------------------------------------------------------------------
# Core conversion tests (isolated via fake HOME)
# ---------------------------------------------------------------------------

@test "sync_agy_memory.sh: version-matching session is converted to Markdown" {
    FAKE_HOME="$(mktemp -d)"
    mkdir -p "${FAKE_HOME}/.gemini/antigravity-cli/brain/conv-abc123/.system_generated/logs"
    cp "${FAKE_BRAIN_MATCH}/conv-abc123/.system_generated/logs/transcript_full.jsonl" \
       "${FAKE_HOME}/.gemini/antigravity-cli/brain/conv-abc123/.system_generated/logs/"

    WORK_DIR="$(mktemp -d)"
    mkdir -p "${WORK_DIR}/.context/ai-memory/0.7.17"
    OLDPWD="$(pwd)"

    cd "$WORK_DIR"
    run env HOME="$FAKE_HOME" bash "${OLDPWD}/scripts/sync_agy_memory.sh" 0.7.17
    cd "$OLDPWD"

    [ "$status" -eq 0 ]
    [[ "$output" == *"conv-abc123.md"* ]] || [[ "$output" == *"synced=1"* ]]
    [ -f "${WORK_DIR}/.context/ai-memory/0.7.17/conv-abc123.md" ]

    rm -rf "$FAKE_HOME" "$WORK_DIR"
}

@test "sync_agy_memory.sh: non-matching session is skipped" {
    FAKE_HOME="$(mktemp -d)"
    mkdir -p "${FAKE_HOME}/.gemini/antigravity-cli/brain/conv-xyz999/.system_generated/logs"
    cp "${FAKE_BRAIN_SKIP}/conv-xyz999/.system_generated/logs/transcript_full.jsonl" \
       "${FAKE_HOME}/.gemini/antigravity-cli/brain/conv-xyz999/.system_generated/logs/"

    WORK_DIR="$(mktemp -d)"
    mkdir -p "${WORK_DIR}/.context/ai-memory/0.7.17"
    OLDPWD="$(pwd)"

    cd "$WORK_DIR"
    run env HOME="$FAKE_HOME" bash "${OLDPWD}/scripts/sync_agy_memory.sh" 0.7.17
    cd "$OLDPWD"

    [ "$status" -eq 0 ]
    [[ "$output" == *"synced=0"* ]]
    [ ! -f "${WORK_DIR}/.context/ai-memory/0.7.17/conv-xyz999.md" ]

    rm -rf "$FAKE_HOME" "$WORK_DIR"
}

@test "sync_agy_memory.sh: up-to-date destination is not overwritten" {
    FAKE_HOME="$(mktemp -d)"
    mkdir -p "${FAKE_HOME}/.gemini/antigravity-cli/brain/conv-abc123/.system_generated/logs"
    cp "${FAKE_BRAIN_MATCH}/conv-abc123/.system_generated/logs/transcript_full.jsonl" \
       "${FAKE_HOME}/.gemini/antigravity-cli/brain/conv-abc123/.system_generated/logs/"

    WORK_DIR="$(mktemp -d)"
    mkdir -p "${WORK_DIR}/.context/ai-memory/0.7.17"
    # Destination is timestamped far in the future — source is older
    touch -t 203001010000 "${WORK_DIR}/.context/ai-memory/0.7.17/conv-abc123.md"
    OLDPWD="$(pwd)"

    cd "$WORK_DIR"
    run env HOME="$FAKE_HOME" bash "${OLDPWD}/scripts/sync_agy_memory.sh" 0.7.17
    cd "$OLDPWD"

    [ "$status" -eq 0 ]
    [[ "$output" == *"skipped_up_to_date=1"* ]]

    rm -rf "$FAKE_HOME" "$WORK_DIR"
}

@test "sync_agy_memory.sh: missing brain dirs are silently skipped" {
    FAKE_HOME="$(mktemp -d)"  # no brain dirs created inside

    WORK_DIR="$(mktemp -d)"
    mkdir -p "${WORK_DIR}/.context/ai-memory/0.7.17"
    OLDPWD="$(pwd)"

    cd "$WORK_DIR"
    run env HOME="$FAKE_HOME" bash "${OLDPWD}/scripts/sync_agy_memory.sh" 0.7.17
    cd "$OLDPWD"

    [ "$status" -eq 0 ]
    [[ "$output" == *"synced=0"* ]]

    rm -rf "$FAKE_HOME" "$WORK_DIR"
}

@test "sync_agy_memory.sh: automated daemon task (CRITICAL prompt) is skipped" {
    FAKE_HOME="$(mktemp -d)"
    mkdir -p "${FAKE_HOME}/.gemini/antigravity-cli/brain/conv-daemon1/.system_generated/logs"
    printf '%s\n' \
        '{"step_index":1,"source":"USER","type":"USER_INPUT","created_at":"2026-09-01T00:00:00Z","content":"System Instructions: You are a knowledge graph expert for 0.7.17\nCRITICAL: Respond ONLY with the requested JSON payload.","thinking":null,"tool_calls":null}' \
        > "${FAKE_HOME}/.gemini/antigravity-cli/brain/conv-daemon1/.system_generated/logs/transcript_full.jsonl"

    WORK_DIR="$(mktemp -d)"
    mkdir -p "${WORK_DIR}/.context/ai-memory/0.7.17"
    OLDPWD="$(pwd)"

    cd "$WORK_DIR"
    run env HOME="$FAKE_HOME" bash "${OLDPWD}/scripts/sync_agy_memory.sh" 0.7.17
    cd "$OLDPWD"

    [ "$status" -eq 0 ]
    [[ "$output" == *"synced=0"* ]]
    [ ! -f "${WORK_DIR}/.context/ai-memory/0.7.17/conv-daemon1.md" ]

    rm -rf "$FAKE_HOME" "$WORK_DIR"
}

@test "sync_agy_memory.sh: automated mykg extraction task prompt is skipped" {
    FAKE_HOME="$(mktemp -d)"
    mkdir -p "${FAKE_HOME}/.gemini/antigravity-cli/brain/conv-extract1/.system_generated/logs"
    printf '%s\n' \
        '{"step_index":1,"source":"USER","type":"USER_INPUT","created_at":"2026-09-01T00:00:00Z","content":"You are extracting knowledge graph entities and edges for myKG task for version 0.7.17","thinking":null,"tool_calls":null}' \
        > "${FAKE_HOME}/.gemini/antigravity-cli/brain/conv-extract1/.system_generated/logs/transcript_full.jsonl"

    WORK_DIR="$(mktemp -d)"
    mkdir -p "${WORK_DIR}/.context/ai-memory/0.7.17"
    OLDPWD="$(pwd)"

    cd "$WORK_DIR"
    run env HOME="$FAKE_HOME" bash "${OLDPWD}/scripts/sync_agy_memory.sh" 0.7.17
    cd "$OLDPWD"

    [ "$status" -eq 0 ]
    [[ "$output" == *"synced=0"* ]]
    [ ! -f "${WORK_DIR}/.context/ai-memory/0.7.17/conv-extract1.md" ]

    rm -rf "$FAKE_HOME" "$WORK_DIR"
}

# ---------------------------------------------------------------------------
# Makefile target tests
# ---------------------------------------------------------------------------

@test "Makefile memory-presync dry-run references sync_agy_memory.sh" {
    run make -n memory-presync
    [ "$status" -eq 0 ]
    [[ "$output" == *"sync_agy_memory.sh"* ]]
}

@test "Makefile memory-presync dry-run patches .iqoqo-mykg-scope.yaml" {
    run make -n memory-presync
    [ "$status" -eq 0 ]
    [[ "$output" == *".iqoqo-mykg-scope.yaml"* ]]
}

@test "Makefile memory-presync does NOT reference external sync-agy-memory" {
    run make -n memory-presync
    [ "$status" -eq 0 ]
    [[ "$output" != *"sync-agy-memory"* ]]
}

@test "Makefile memory-presync does NOT reference external copy-agy-version" {
    run make -n memory-presync
    [ "$status" -eq 0 ]
    [[ "$output" != *"copy-agy-version"* ]]
}

# ---------------------------------------------------------------------------
# .iqoqo-mykg-scope.yaml integrity tests
# ---------------------------------------------------------------------------

@test ".iqoqo-mykg-scope.yaml is tracked in git" {
    run git ls-files .iqoqo-mykg-scope.yaml
    [ "$status" -eq 0 ]
    [[ "$output" == *".iqoqo-mykg-scope.yaml"* ]]
}

@test ".iqoqo-mykg-scope.yaml contains a versioned ai-memory path" {
    run grep -E '\.context/ai-memory/[0-9]+\.[0-9]+\.[0-9]+' .iqoqo-mykg-scope.yaml
    [ "$status" -eq 0 ]
}

@test "sed patch for .iqoqo-mykg-scope.yaml is idempotent" {
    VERSION="$(python3 -c "import json; print(json.load(open('package.json'))['version'])")"
    # Apply the same sed substitution twice — result must still contain exactly one versioned path
    sed -i "s|\.context/ai-memory/[0-9][0-9.]*|.context/ai-memory/${VERSION}|g" .iqoqo-mykg-scope.yaml
    sed -i "s|\.context/ai-memory/[0-9][0-9.]*|.context/ai-memory/${VERSION}|g" .iqoqo-mykg-scope.yaml
    run grep "ai-memory/${VERSION}" .iqoqo-mykg-scope.yaml
    [ "$status" -eq 0 ]
    # Exactly one match expected
    [ "$(grep -c "ai-memory/${VERSION}" .iqoqo-mykg-scope.yaml)" -eq 1 ]
}

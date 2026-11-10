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

setup() {
    TEST_TMPDIR="$(mktemp -d)"
    cp .env.example "$TEST_TMPDIR/.env.example"
}

teardown() {
    rm -rf "$TEST_TMPDIR"
}

@test "iqoqo_installer non-interactive creates hardened 0600 .env" {
    run python3 scripts/iqoqo_installer.py \
        --domain "node.test" \
        --mode standard \
        --env-file "$TEST_TMPDIR/.env" \
        --example-file "$TEST_TMPDIR/.env.example" \
        --non-interactive

    [ "$status" -eq 0 ]
    [ -f "$TEST_TMPDIR/.env" ]

    # Test file mode is 0600
    PERMS="$(stat -c "%a" "$TEST_TMPDIR/.env")"
    [ "$PERMS" = "600" ]

    # Test federation head is false in standard mode
    grep -q 'FEDERATION_HEAD_MODE="false"' "$TEST_TMPDIR/.env"
}

@test "iqoqo_installer supports federation_head mode" {
    run python3 scripts/iqoqo_installer.py \
        --domain "hub.test" \
        --mode federation_head \
        --env-file "$TEST_TMPDIR/.env" \
        --example-file "$TEST_TMPDIR/.env.example" \
        --non-interactive

    [ "$status" -eq 0 ]
    grep -q 'FEDERATION_HEAD_MODE="true"' "$TEST_TMPDIR/.env"
}

@test "iqoqo_installer presync-check passes on generated environment" {
    run python3 scripts/iqoqo_installer.py \
        --domain "localhost:5000" \
        --mode standard \
        --env-file "$TEST_TMPDIR/.env" \
        --example-file "$TEST_TMPDIR/.env.example" \
        --non-interactive

    [ "$status" -eq 0 ]

    run python3 scripts/iqoqo_installer.py \
        --presync-check \
        --env-file "$TEST_TMPDIR/.env"

    [ "$status" -eq 0 ]
    [[ "$output" =~ "READY" ]] || [[ "$output" =~ "requirements satisfied" ]]
}

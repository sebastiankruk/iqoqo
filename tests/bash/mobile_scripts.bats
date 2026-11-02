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
# tests/bash/mobile_scripts.bats
# Validates Android SDK and emulator helper scripts behavior.

setup() {
  export TEST_TMPDIR="$BATS_TMPDIR/iqoqo_mobile_test_$$"
  mkdir -p "$TEST_TMPDIR"
}

teardown() {
  rm -rf "$TEST_TMPDIR"
}

@test "setup-android-sdk.sh --help prints usage and exits 0" {
  run ./scripts/setup-android-sdk.sh --help
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Usage:" ]]
}

@test "setup-android-sdk.sh --dry-run exits 0" {
  run ./scripts/setup-android-sdk.sh --dry-run
  [ "$status" -eq 0 ]
  [[ "$output" =~ "DRY RUN" ]]
}

@test "setup-android-sdk.sh --check-only fails when SDK is absent" {
  ANDROID_HOME="$TEST_TMPDIR/nonexistent-sdk" run ./scripts/setup-android-sdk.sh --check-only
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Android SDK components missing" ]]
}

@test "setup-android-sdk.sh --check-only passes when mocked tools exist" {
  MOCK_SDK="$TEST_TMPDIR/mock-sdk"
  mkdir -p "$MOCK_SDK/cmdline-tools/latest/bin"
  mkdir -p "$MOCK_SDK/platforms/android-35"
  mkdir -p "$MOCK_SDK/build-tools/35.0.0"
  touch "$MOCK_SDK/cmdline-tools/latest/bin/sdkmanager"
  chmod +x "$MOCK_SDK/cmdline-tools/latest/bin/sdkmanager"

  ANDROID_HOME="$MOCK_SDK" run ./scripts/setup-android-sdk.sh --check-only
  [ "$status" -eq 0 ]
}

@test "setup-android-emulator.sh --help prints usage and exits 0" {
  run ./scripts/setup-android-emulator.sh --help
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Usage:" ]]
}

@test "setup-android-emulator.sh --dry-run exits 0" {
  run ./scripts/setup-android-emulator.sh --dry-run
  [ "$status" -eq 0 ]
  [[ "$output" =~ "DRY RUN" ]]
}

@test "setup-android-emulator.sh --check-only fails when tools are absent" {
  ANDROID_HOME="$TEST_TMPDIR/nonexistent-sdk" run ./scripts/setup-android-emulator.sh --check-only
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Android SDK tools missing" ]]
}

@test "setup-android-emulator.sh --check-only passes when mocked tools exist" {
  MOCK_SDK="$TEST_TMPDIR/mock-sdk-emu"
  mkdir -p "$MOCK_SDK/cmdline-tools/latest/bin"
  touch "$MOCK_SDK/cmdline-tools/latest/bin/sdkmanager"
  touch "$MOCK_SDK/cmdline-tools/latest/bin/avdmanager"
  chmod +x "$MOCK_SDK/cmdline-tools/latest/bin/sdkmanager" "$MOCK_SDK/cmdline-tools/latest/bin/avdmanager"

  ANDROID_HOME="$MOCK_SDK" run ./scripts/setup-android-emulator.sh --check-only
  [ "$status" -eq 0 ]
}

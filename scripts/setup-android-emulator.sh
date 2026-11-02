#!/usr/bin/env bash
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
# scripts/setup-android-emulator.sh
#
# Setup script to provision and spin up a headless Android emulator
# (iqoqo-test) for native integration and Playwright/Appium testing.

set -euo pipefail

if [[ "$OSTYPE" == "darwin"* ]]; then
    DEFAULT_ANDROID_HOME="$HOME/Library/Android/sdk"
else
    DEFAULT_ANDROID_HOME="$HOME/.android-sdk"
fi

ANDROID_HOME="${ANDROID_HOME:-$DEFAULT_ANDROID_HOME}"
SDKMANAGER="$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager"
AVDMANAGER="$ANDROID_HOME/cmdline-tools/latest/bin/avdmanager"
EMULATOR="$ANDROID_HOME/emulator/emulator"

CHECK_ONLY=false
DRY_RUN=false

for arg in "$@"; do
    case "$arg" in
        --check|--check-only)
            CHECK_ONLY=true
            ;;
        --dry-run)
            DRY_RUN=true
            ;;
        -h|--help)
            echo "Usage: $0 [--check-only] [--dry-run]"
            echo "Provisions and starts headless Android emulator (iqoqo-test)."
            exit 0
            ;;
        *)
            ;;
    esac
done

if [ -n "${IQOQO_AI_MODE:-}" ]; then
    log() { :; }
    log_info() { :; }
else
    log() { echo "$@"; }
    log_info() { echo "ℹ️  $*"; }
fi

if [ "$CHECK_ONLY" = true ]; then
    if [ -x "$SDKMANAGER" ] && [ -x "$AVDMANAGER" ]; then
        log_info "Android SDK management tools found in $ANDROID_HOME."
        exit 0
    else
        echo "Android SDK tools missing in $ANDROID_HOME." >&2
        exit 1
    fi
fi

ARCH=$(uname -m)
if [ "$ARCH" = "x86_64" ]; then
    SYS_IMG_ARCH="x86_64"
elif [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
    SYS_IMG_ARCH="arm64-v8a"
else
    SYS_IMG_ARCH="x86_64"
fi

SYSTEM_IMAGE="system-images;android-34;google_apis;$SYS_IMG_ARCH"

if [ "$DRY_RUN" = true ]; then
    echo "DRY RUN: Would verify $ANDROID_HOME, install $SYSTEM_IMAGE, create AVD 'iqoqo-test', and launch emulator."
    exit 0
fi

if [ ! -x "$SDKMANAGER" ]; then
    echo "ERROR: sdkmanager not found at $SDKMANAGER" >&2
    echo "Please run scripts/setup-android-sdk.sh first." >&2
    exit 1
fi

log_info "Installing emulator package and system image ($SYSTEM_IMAGE)..."
"$SDKMANAGER" "emulator" "$SYSTEM_IMAGE" >/dev/null

log_info "Creating Android Virtual Device (iqoqo-test)..."
echo "no" | "$AVDMANAGER" create avd -n iqoqo-test -k "$SYSTEM_IMAGE" --force >/dev/null

log_info "Booting Android emulator in headless mode..."
if [ -x "$EMULATOR" ]; then
    "$EMULATOR" -avd iqoqo-test -no-window -no-audio -no-boot-anim &
    log_info "Headless Android emulator started in background."
else
    echo "WARNING: Emulator binary not found at $EMULATOR. AVD created." >&2
fi

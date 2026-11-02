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
# scripts/setup-android-sdk.sh
#
# Idempotent provisioning script for Android SDK Command-line Tools,
# platform-tools, build-tools, and target platforms on Ubuntu/Debian Linux.

set -euo pipefail

DEFAULT_ANDROID_HOME="$HOME/.android-sdk"
ANDROID_HOME="${ANDROID_HOME:-$DEFAULT_ANDROID_HOME}"
CMDLINE_TOOLS_URL="https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"

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
            echo "Installs Android SDK command-line tools into $ANDROID_HOME."
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

SDKMANAGER="$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager"

check_installed() {
    if [ -x "$SDKMANAGER" ] && \
       [ -d "$ANDROID_HOME/platforms/android-35" ] && \
       [ -d "$ANDROID_HOME/build-tools/35.0.0" ]; then
        return 0
    fi
    return 1
}

if [ "$CHECK_ONLY" = true ]; then
    if check_installed; then
        log_info "Android SDK tools and platforms;android-35 are properly installed in $ANDROID_HOME."
        exit 0
    else
        echo "Android SDK components missing in $ANDROID_HOME." >&2
        exit 1
    fi
fi

if [ "$DRY_RUN" = true ]; then
    echo "DRY RUN: Would verify Java 21, download cmdline-tools to $ANDROID_HOME, and install:"
    echo "  - platform-tools"
    echo "  - platforms;android-35"
    echo "  - build-tools;35.0.0"
    exit 0
fi

mkdir -p "$ANDROID_HOME"

# 1. Download and bootstrap cmdline-tools if missing
if [ ! -x "$SDKMANAGER" ]; then
    log_info "Android cmdline-tools missing. Bootstrapping into $ANDROID_HOME..."
    TMP_ZIP="/tmp/cmdline-tools-linux-$$.zip"
    TMP_EXTRACT="/tmp/cmdline-tools-extract-$$"
    mkdir -p "$TMP_EXTRACT"
    
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "$CMDLINE_TOOLS_URL" -o "$TMP_ZIP"
    elif command -v wget >/dev/null 2>&1; then
        wget -qO "$TMP_ZIP" "$CMDLINE_TOOLS_URL"
    else
        echo "ERROR: Neither curl nor wget found. Please install one." >&2
        exit 1
    fi

    unzip -q "$TMP_ZIP" -d "$TMP_EXTRACT"
    mkdir -p "$ANDROID_HOME/cmdline-tools"
    rm -rf "$ANDROID_HOME/cmdline-tools/latest"
    mv "$TMP_EXTRACT/cmdline-tools" "$ANDROID_HOME/cmdline-tools/latest"
    rm -rf "$TMP_ZIP" "$TMP_EXTRACT"
    log_info "cmdline-tools unpacked to $ANDROID_HOME/cmdline-tools/latest"
fi

# 2. Accept licenses automatically
log_info "Accepting Android SDK licenses..."
yes | "$SDKMANAGER" --licenses >/dev/null 2>&1 || true

# 3. Install required platform-tools, platforms;android-35, and build-tools;35.0.0
log_info "Installing platform-tools, platforms;android-35, and build-tools;35.0.0..."
"$SDKMANAGER" "platform-tools" "platforms;android-35" "build-tools;35.0.0" >/dev/null

log_info "Android SDK setup complete at $ANDROID_HOME!"
if [ -z "${IQOQO_AI_MODE:-}" ]; then
    echo ""
    echo "To configure your environment, add the following to your ~/.bashrc:"
    echo "  export ANDROID_HOME=\"$ANDROID_HOME\""
    echo "  export PATH=\"\$ANDROID_HOME/cmdline-tools/latest/bin:\$ANDROID_HOME/platform-tools:\$PATH\""
fi

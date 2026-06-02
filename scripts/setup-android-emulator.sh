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
# Setup script for developers to spin up a headless Android emulator
# for local native integration testing.

set -euo pipefail

ANDROID_HOME="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
SDKMANAGER="$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager"
AVDMANAGER="$ANDROID_HOME/cmdline-tools/latest/bin/avdmanager"
EMULATOR="$ANDROID_HOME/emulator/emulator"

echo "Using ANDROID_HOME: $ANDROID_HOME"

if [ ! -f "$SDKMANAGER" ]; then
    echo "ERROR: sdkmanager not found at $SDKMANAGER"
    echo "Please ensure Android SDK Command-line Tools are installed."
    exit 1
fi

echo "Installing system image (API 34, Google APIs, ARM64)..."
"$SDKMANAGER" "system-images;android-34;google_apis;arm64-v8a"

echo "Creating Android Virtual Device (iqoqo-test)..."
echo "no" | "$AVDMANAGER" create avd -n iqoqo-test -k "system-images;android-34;google_apis;arm64-v8a" --force

echo "Booting Android emulator in headless mode..."
"$EMULATOR" -avd iqoqo-test -no-window -no-audio -no-boot-anim &

echo "Headless Android emulator starting in the background."

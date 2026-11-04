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
# scripts/setup-ios-tools.sh
#
# Idempotent provisioning script for iOS build tooling (CocoaPods)
# on macOS using user-level Ruby gems without Homebrew compilation.

set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "==> Error: iOS tooling can only be provisioned on macOS." >&2
  exit 1
fi

USER_GEM_BIN="$(ruby -e 'puts Gem.bindir(Gem.user_dir)' 2>/dev/null || echo "$HOME/.gem/ruby/2.6.0/bin")"
if [[ -d "$USER_GEM_BIN" ]]; then
  export PATH="$USER_GEM_BIN:$PATH"
fi

if command -v pod >/dev/null 2>&1; then
  echo "==> CocoaPods is already installed: $(pod --version) ($USER_GEM_BIN/pod)"
  exit 0
fi

echo "==> Provisioning CocoaPods for macOS system Ruby..."
echo "    Installing compatible pinned gems (skipping Homebrew LLVM compilation)..."

gem install ffi -v 1.15.5 --user-install --no-document
gem install zeitwerk -v 2.6.18 --user-install --no-document
gem install i18n -v 1.14.8 --user-install --no-document
gem install cocoapods -v 1.16.2 --user-install --no-document

if [[ -x "$USER_GEM_BIN/pod" ]]; then
  export PATH="$USER_GEM_BIN:$PATH"
  echo "==> CocoaPods installed successfully: $("$USER_GEM_BIN/pod" --version)"
  echo ""
  echo "    NOTE: Ensure the following line is in your ~/.zshrc or ~/.bash_profile:"
  echo ""
  echo "    export PATH=\"$USER_GEM_BIN:\$PATH\""
  echo ""
else
  echo "==> Error: pod binary was not found at $USER_GEM_BIN/pod" >&2
  exit 1
fi

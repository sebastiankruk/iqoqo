#!/bin/bash
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

# Configuration
AUTHOR_SIGNATURE="Sebastian Ryszard Kruk (dev@kruk.me)"
LICENSE_SIGNATURE="GNU Affero General Public License"

# File extensions to check (add or remove as needed)
EXTENSIONS=("*.ts" "*.tsx" "*.js" "*.py" "*.java" "*.go" "*.rs" "*.cpp" "*.c" "*.h" "*.sh" "*.yaml" "*.yml" "Dockerfile*" "Makefile*" "*.css" "*.svg")

echo "Checking source files for license headers..."
FAILED=0

# Find files and check content
while IFS= read -r file; do
    # Skip if file doesn't exist (e.g. deleted but in git index)
    if [ ! -f "$file" ]; then
        continue
    fi

    # Check if file matches any extension pattern
    MATCH=0
    filename=$(basename "$file")
    for ext in "${EXTENSIONS[@]}"; do
        # shellcheck disable=SC2053
        if [[ "$filename" == $ext ]] && [[ "$file" != frontend/public/* ]]; then
            MATCH=1
            break
        fi
    done

    if [ $MATCH -eq 0 ]; then
        continue
    fi

    if ! grep -Fq "$AUTHOR_SIGNATURE" "$file"; then
        echo "❌ Missing copyright info: $file"
        FAILED=1
    elif ! grep -Fq "$LICENSE_SIGNATURE" "$file"; then
        echo "❌ Missing license info:   $file"
        FAILED=1
    fi
done < <(git ls-files -c -o --exclude-standard)

if [ $FAILED -eq 0 ]; then
    echo "✅ All source files contain the correct license header."
    exit 0
else
    echo "⚠️  Some files are missing license headers."
    exit 1
fi

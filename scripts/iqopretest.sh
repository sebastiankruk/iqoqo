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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# 1. Verify project version
make version
make preview-down

# 2. Build local Docker images tagged with 'preview'
echo "🔨 Building preview Docker images..."
if ! make docker-build-preview; then
    echo "💥 ERROR: Preview Docker image build failed! Stop immediately so old container does not run." >&2
    exit 1
fi

if [ "${SKIP_CLONE:-0}" = "1" ]; then
    echo "Skipping cloning"
else
    # 5. Clone prod
    make clone \
        src_host=h.kruk.me \
        src_loc=/opt/iqoqo \
        src_name=prod \
        dst_loc=/opt/pre.iqoqo \
        dst_name=preview
fi

FEDERATION_PAIR="${FEDERATION_PAIR:-0}"
for arg in "$@"; do
    case "$arg" in
        --federation-pair|--federation)
            FEDERATION_PAIR="1"
            ;;
    esac
done

# 6. Restart preview stack cleanly
make preview-down
make preview-up FEDERATION_PAIR="$FEDERATION_PAIR"

# 7. Verify final version
make status preview

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
# Mock-based test for cloud_backup.sh

set -e

echo "🧪 Testing cloud_backup.sh logic..."

# Create mock environment
TEST_DIR=$(mktemp -d)
BIN_DIR="${TEST_DIR}/bin"
mkdir -p "${BIN_DIR}"

# Mock docker (cloud_backup.sh invokes `docker compose ... exec -T db pg_dumpall ...`)
cat <<EOF > "${BIN_DIR}/docker"
#!/bin/bash
if [ "\$1" == "compose" ] || [ "\$1" == "exec" ]; then
    echo "DUMMY SQL DATA"
fi
EOF
chmod +x "${BIN_DIR}/docker"

# Mock rclone
cat <<EOF > "${BIN_DIR}/rclone"
#!/bin/bash
if [ "\$1" == "copy" ]; then
    if [ -f "\$2" ]; then
        echo "Mock upload success: \$2 to \$3"
    else
        echo "Error: File \$2 not found"
        exit 1
    fi
fi
EOF
chmod +x "${BIN_DIR}/rclone"

export PATH="${BIN_DIR}:${PATH}"
export COMPOSE_PROJECT_NAME="iqoqo-test"
export POSTGRES_USER="testuser"

# Run the script
bash ./scripts/cloud_backup.sh test-remote

# Verify cleanup
if ls /tmp/iqoqo_backup_*.tar.gz 1>/dev/null 2>&1; then
    echo "❌ Fail: Local archive was not cleaned up"
    exit 1
fi

echo "✅ Success: cloud_backup.sh logic verified"
rm -rf "${TEST_DIR}"

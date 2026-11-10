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
# Standalone bootstrap installer script for iQoQo.
# Downloads and invokes the iQoQo CLI wizard into a target deployment directory.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/sebastiankruk/iqoqo/release/1.0.2/scripts/install.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/sebastiankruk/iqoqo/release/1.0.2/scripts/install.sh | bash -s -- -d /opt/pre.iqoqo --mode preview

set -euo pipefail

BRANCH_OR_TAG="${IQOQO_BRANCH:-release/1.0.2}"
RAW_BASE_URL="https://raw.githubusercontent.com/sebastiankruk/iqoqo/${BRANCH_OR_TAG}"
DEFAULT_TARGET_DIR="${IQOQO_DIR:-.}"

TARGET_DIR="${DEFAULT_TARGET_DIR}"
FORWARD_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -d|--dir)
      TARGET_DIR="$2"
      shift 2
      ;;
    *)
      FORWARD_ARGS+=("$1")
      shift
      ;;
  esac
done

echo "=========================================================="
echo "          iQoQo Bootstrap Installer (${BRANCH_OR_TAG})"
echo "=========================================================="
echo "Target directory: ${TARGET_DIR}"

# 1. Host prerequisite check
if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required on the host but not installed." >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "Error: curl is required on the host but not installed." >&2
  exit 1
fi

# 2. Prepare target directory
if [[ ! -d "${TARGET_DIR}" ]]; then
  echo "Creating target directory: ${TARGET_DIR}..."
  mkdir -p "${TARGET_DIR}"
fi

cd "${TARGET_DIR}"

# 3. Download standalone installer script
if [[ -f "./scripts/iqoqo_installer.py" ]]; then
  INSTALLER_EXEC="./scripts/iqoqo_installer.py"
elif [[ -f "./iqoqo_installer.py" ]]; then
  INSTALLER_EXEC="./iqoqo_installer.py"
else
  echo "Fetching installer wizard from ${BRANCH_OR_TAG}..."
  curl -fsSL "${RAW_BASE_URL}/scripts/iqoqo_installer.py" -o iqoqo_installer.py
  chmod +x iqoqo_installer.py
  INSTALLER_EXEC="./iqoqo_installer.py"
fi

# 4. Execute installer
echo "Launching iQoQo setup wizard..."
python3 "${INSTALLER_EXEC}" "${FORWARD_ARGS[@]}"

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
#   curl -fsSL https://raw.githubusercontent.com/sebastiankruk/iqoqo/main/scripts/install.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/sebastiankruk/iqoqo/main/scripts/install.sh | bash -s -- -d /opt/preview.iqoqo --mode preview

set -euo pipefail

# Accept IQOQO_BRANCH, BRANCH_OR_TAG, or default to main
BRANCH_OR_TAG="${IQOQO_BRANCH:-${BRANCH_OR_TAG:-main}}"
# Normalize if user passes refs/heads/ or full git ref
BRANCH_OR_TAG="${BRANCH_OR_TAG#refs/heads/}"
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
    -b|--branch)
      BRANCH_OR_TAG="$2"
      BRANCH_OR_TAG="${BRANCH_OR_TAG#refs/heads/}"
      RAW_BASE_URL="https://raw.githubusercontent.com/sebastiankruk/iqoqo/${BRANCH_OR_TAG}"
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
  # Try primary branch URL first, fall back to release/1.0.2 or main if custom branch doesn't have it
  if ! curl -fsSL "${RAW_BASE_URL}/scripts/iqoqo_installer.py" -o iqoqo_installer.py 2>/dev/null; then
    echo "Notice: Branch ${BRANCH_OR_TAG} not found on remote. Trying fallback branches..."
    FALLBACK_BRANCHES=("main" "release/1.0.2")
    FOUND=0
    for FB in "${FALLBACK_BRANCHES[@]}"; do
      if curl -fsSL "https://raw.githubusercontent.com/sebastiankruk/iqoqo/${FB}/scripts/iqoqo_installer.py" -o iqoqo_installer.py 2>/dev/null; then
        echo "Found installer wizard on branch ${FB}."
        FOUND=1
        break
      fi
    done
    if [[ $FOUND -ne 1 ]]; then
      echo "Error: Failed to download scripts/iqoqo_installer.py from ${BRANCH_OR_TAG} or fallback branches." >&2
      exit 1
    fi
  fi
  chmod +x iqoqo_installer.py
  INSTALLER_EXEC="./iqoqo_installer.py"
fi

# 4. Download compose specifications if not in git checkout
if [[ ! -f "./docker-compose.yml" ]]; then
  echo "Fetching Docker Compose specifications..."
  curl -fsSL "${RAW_BASE_URL}/docker-compose.yml" -o docker-compose.yml 2>/dev/null || \
    curl -fsSL "https://raw.githubusercontent.com/sebastiankruk/iqoqo/main/docker-compose.yml" -o docker-compose.yml
fi
if [[ ! -f "./docker-compose.prebuilt.yml" ]]; then
  curl -fsSL "${RAW_BASE_URL}/docker-compose.prebuilt.yml" -o docker-compose.prebuilt.yml 2>/dev/null || \
    curl -fsSL "https://raw.githubusercontent.com/sebastiankruk/iqoqo/main/docker-compose.prebuilt.yml" -o docker-compose.prebuilt.yml
fi
if [[ ! -f "./docker-compose.monitoring.yml" ]]; then
  curl -fsSL "${RAW_BASE_URL}/docker-compose.monitoring.yml" -o docker-compose.monitoring.yml 2>/dev/null || \
    curl -fsSL "https://raw.githubusercontent.com/sebastiankruk/iqoqo/main/docker-compose.monitoring.yml" -o docker-compose.monitoring.yml
fi
mkdir -p deploy
if [[ ! -f "./deploy/nginx.conf" ]]; then
  curl -fsSL "${RAW_BASE_URL}/deploy/nginx.conf" -o deploy/nginx.conf 2>/dev/null || \
    curl -fsSL "https://raw.githubusercontent.com/sebastiankruk/iqoqo/main/deploy/nginx.conf" -o deploy/nginx.conf
fi

# Ensure bind mount directory structures and permissions
mkdir -p app/static/covers app/static/gallery app/static/uploads/raw_covers data/keys exports
chmod -R a+rwX app/static/covers app/static/gallery app/static/uploads/raw_covers data exports 2>/dev/null || true
if [[ -d data/keys ]]; then chmod 1777 data/keys 2>/dev/null || true; chmod 600 data/keys/*.pem 2>/dev/null || true; fi

# 5. Execute installer
echo "Launching iQoQo setup wizard..."
python3 "${INSTALLER_EXEC}" "${FORWARD_ARGS[@]}"

echo ""
echo "=========================================================="
echo "          Setup Complete!"
echo "=========================================================="
echo "Next step to start your iQoQo instance:"
echo ""
echo "  docker compose -f docker-compose.prebuilt.yml up -d"
echo ""
echo "To check logs and status:"
echo "  docker compose logs -f"
echo "  python3 ${INSTALLER_EXEC} --presync-check"
echo "=========================================================="

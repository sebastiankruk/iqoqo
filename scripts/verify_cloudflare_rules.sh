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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
RULES_DOC="${ROOT_DIR}/deploy/cloudflare-semantic-federation-rules.md"

echo "=== Verifying Cloudflare Semantic & Fediverse Rules Configuration ==="

# 1. Structural Verification of Codified Rules Documentation
if [[ ! -f "${RULES_DOC}" ]]; then
  echo "[-] ERROR: Rules documentation not found at ${RULES_DOC}" >&2
  exit 1
fi

REQUIRED_ELEMENTS=(
  "/.well-known/webfinger"
  "/.well-known/nodeinfo"
  "/api/federation/"
  "/api/public/rdf/"
  "application/activity+json"
  "application/jrd+json"
  "application/ld+json"
  "text/turtle"
  "http_request_firewall_custom"
)

echo "[*] Verifying required paths and MIME selectors in ${RULES_DOC}..."
for element in "${REQUIRED_ELEMENTS[@]}"; do
  if ! grep -Fq "${element}" "${RULES_DOC}"; then
    echo "[-] ERROR: Missing required rule element: '${element}'" >&2
    exit 2
  fi
done
echo "[+] All required path prefixes and MIME types codified in documentation."

# 2. Live HTTP Verification (when URL is provided or IQOQO_URL is set)
TARGET_URL="${1:-${IQOQO_URL:-}}"

if [[ -n "${TARGET_URL}" ]]; then
  echo "[*] Probing live endpoint at ${TARGET_URL} for Cloudflare challenge bypass..."
  
  # Ensure target URL does not end with trailing slash
  TARGET_URL="${TARGET_URL%/}"

  check_endpoint() {
    local path="$1"
    local accept_header="$2"
    local desc="$3"
    local url="${TARGET_URL}${path}"

    echo "  -> Probing ${desc} (${path}) with Accept: ${accept_header}..."
    local response
    response=$(curl -sSL -H "Accept: ${accept_header}" -H "User-Agent: ActivityPub-Fediverse-Crawler/1.0" -w "\n%{http_code}" "${url}" || echo "CURL_ERROR")

    if [[ "${response}" == "CURL_ERROR" ]]; then
      echo "  [-] WARN: Could not reach ${url} (network or DNS error)" >&2
      return 0
    fi

    local http_code
    http_code=$(echo "${response}" | tail -n1)
    local body
    body=$(echo "${response}" | sed '$d')

    if echo "${body}" | grep -Ei "(cf-mitigated|just a moment\.\.\.|attention required! \| cloudflare)" >/dev/null; then
      echo "  [-] ERROR: Cloudflare challenge page detected on ${path} (HTTP ${http_code})!" >&2
      return 1
    fi

    echo "  [+] OK: Endpoint returned HTTP ${http_code} without Cloudflare challenge."
  }

  check_endpoint "/.well-known/webfinger?resource=acct:probe@iqoqo.kruk.cc" "application/jrd+json" "WebFinger Discovery"
  check_endpoint "/api/federation/actor" "application/activity+json" "Instance Actor Profile"
  check_endpoint "/api/public/rdf/context" "application/ld+json" "JSON-LD Context"
fi

echo "[+] Cloudflare Semantic & Fediverse rules verification completed successfully."
exit 0

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
# 0.6.0-2-manual_test_automation.sh
# Automated walkthrough of the Phase 2 Manual Test Plan: API Security & Payload Validation
# 🦖 Me make script for you!

set -e

# Configuration - Source from .env and .env.dev
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

if [ -f "${ROOT_DIR}/.env" ]; then
    echo "⚡ Loading .env..."
    set -o allexport
    source "${ROOT_DIR}/.env"
    set +o allexport
fi

if [ -f "${ROOT_DIR}/.env.dev" ]; then
    echo "⚡ Loading .env.dev..."
    set -o allexport
    source "${ROOT_DIR}/.env.dev"
    set +o allexport
fi

# Use values from env or fallback to defaults
BASE_URL="${NEXT_PUBLIC_APP_URL:-https://dev.iqoqo.cc}/api"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@iqoqo.local}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-secure_admin_password}"
TEST_USER_EMAIL="testuser_$(date +%s)@iqoqo.local"
TEST_USER_PASSWORD="testpassword123"

echo "🦖 Initializing automated test walkthrough..."

# Utility for colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

function pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

function fail() {
    echo -e "${RED}[FAIL]${NC} $1"
}

# 1. Get Admin Token
echo "🔐 Logging in as Admin..."
ADMIN_TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$ADMIN_EMAIL\", \"password\": \"$ADMIN_PASSWORD\"}" | jq -r .token)

if [ "$ADMIN_TOKEN" == "null" ] || [ -z "$ADMIN_TOKEN" ]; then
    fail "Could not get Admin Token. Check credentials or if server is running."
    exit 1
fi
pass "Admin authenticated."

# 2. Register Normal User
echo "👤 Registering normal user..."
NORMAL_TOKEN=$(curl -s -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$TEST_USER_EMAIL\", \"password\": \"$TEST_USER_PASSWORD\", \"display_name\": \"Test User\"}" | jq -r .token)

if [ "$NORMAL_TOKEN" == "null" ] || [ -z "$NORMAL_TOKEN" ]; then
    fail "Could not register normal user."
    exit 1
fi
pass "Normal user registered and authenticated."

echo "--------------------------------------------------"
echo "🌊 1. Rate Limiting (Flood Protection)"
# Test 1.1: Send request as normal user.
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/isbn/9780141036144" \
  -H "Authorization: Bearer $NORMAL_TOKEN")

if [ "$STATUS" == "200" ] || [ "$STATUS" == "404" ]; then
    pass "Test 1.1: Request as normal user ($STATUS OK/NotFound)."
else
    fail "Test 1.1: Expected 200/404, got $STATUS."
fi

# Test 1.2: Send 11 requests in 1 minute (limit is 10/min).
echo "  Sending 11 requests to trigger rate limit..."
for i in {1..11}; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/isbn/9780141036144" \
      -H "Authorization: Bearer $NORMAL_TOKEN")
    echo -n " $STATUS"
    if [ $i -eq 11 ] && [ "$STATUS" == "429" ]; then
        echo ""
        pass "Test 1.2: 11th request returned 429 Too Many Requests."
    elif [ $i -eq 11 ]; then
        echo ""
        fail "Test 1.2: 11th request did NOT return 429 (got $STATUS)."
    fi
done

echo "--------------------------------------------------"
echo "🧐 2. Payload Validation (Good Data Only)"
# Test 2.1: Valid JSON
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/items/manual" \
  -H "Authorization: Bearer $NORMAL_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"Title\": \"Automated Test Book\", \"Authors\": [\"Test Bot\"], \"Format\": \"book\"}")

if [ "$STATUS" == "200" ]; then
    pass "Test 2.1: Valid JSON returned 200."
else
    fail "Test 2.1: Expected 200, got $STATUS."
fi

# Test 2.2: Invalid JSON (missing bracket)
RESPONSE=$(curl -s -X POST "$BASE_URL/items/manual" \
  -H "Authorization: Bearer $NORMAL_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"Title\": \"Invalid JSON\"")
ERROR=$(echo $RESPONSE | jq -r .error)

if [[ "$ERROR" == "Invalid or missing JSON payload" ]]; then
    pass "Test 2.2: Invalid JSON returned 400 with correct error message."
else
    fail "Test 2.2: Expected 'Invalid or missing JSON payload', got '$ERROR'."
fi

# Test 2.3: Missing required fields
RESPONSE=$(curl -s -X POST "$BASE_URL/items/manual" \
  -H "Authorization: Bearer $NORMAL_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"Authors\": [\"Test Bot\"]}")
ERROR=$(echo $RESPONSE | jq -r .error)

if [[ "$ERROR" == "Invalid payload" ]]; then
    pass "Test 2.3: Missing required fields returned 400 with correct error message."
else
    fail "Test 2.3: Expected 'Invalid payload', got '$ERROR'."
fi

echo "--------------------------------------------------"
echo "🔐 3. Auth Hardening (No Entry for Strangers)"
# Test 3.1: No Auth
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/v1/admin/users")
if [ "$STATUS" == "401" ]; then
    pass "Test 3.1: No Auth returned 401."
else
    fail "Test 3.1: Expected 401, got $STATUS."
fi

# Test 3.2: Normal user accessing admin endpoint
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/v1/admin/users" \
  -H "Authorization: Bearer $NORMAL_TOKEN")
if [ "$STATUS" == "403" ]; then
    pass "Test 3.2: Normal user accessing admin returned 403."
else
    fail "Test 3.2: Expected 403, got $STATUS."
fi

# Test 3.3: Admin user accessing admin endpoint
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/v1/admin/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN")
if [ "$STATUS" == "200" ]; then
    pass "Test 3.3: Admin user accessing admin returned 200."
else
    fail "Test 3.3: Expected 200, got $STATUS."
fi

echo "--------------------------------------------------"
echo "🛡️ 4. BOLA Protection (No Stealing Identity)"
# Setup: Create an item for normal user
ITEM_ID=$(curl -s -X POST "$BASE_URL/items/manual" \
  -H "Authorization: Bearer $NORMAL_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"Title\": \"BOLA Test Item\", \"Authors\": [\"Test Bot\"], \"Format\": \"book\"}" | jq -r .data.item_id)

# Test 4.1: Update own item
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X PUT "$BASE_URL/items/$ITEM_ID" \
  -H "Authorization: Bearer $NORMAL_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"status\": \"reading\"}")
if [ "$STATUS" == "200" ]; then
    pass "Test 4.1: Updating own item returned 200."
else
    fail "Test 4.1: Expected 200, got $STATUS."
fi

# Test 4.2: Update owner_id (BOLA attempt)
RESPONSE=$(curl -s -X PUT "$BASE_URL/items/$ITEM_ID" \
  -H "Authorization: Bearer $NORMAL_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"owner_id\": \"some-other-uuid\"}")
ERROR=$(echo $RESPONSE | jq -r .error)
if [[ "$ERROR" == "Invalid payload: forbidden fields" ]]; then
    pass "Test 4.2: Attempt to update owner_id returned 400 with correct error message."
else
    fail "Test 4.2: Expected 'Invalid payload: forbidden fields', got '$ERROR'."
fi

# Test 4.3: Update someone else's item (Admin item)
# Create an item for Admin first
ADMIN_ITEM_ID=$(curl -s -X POST "$BASE_URL/items/manual" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"Title\": \"Admin Private Item\", \"Authors\": [\"Admin\"], \"Format\": \"book\"}" | jq -r .data.item_id)

STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X PUT "$BASE_URL/items/$ADMIN_ITEM_ID" \
  -H "Authorization: Bearer $NORMAL_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"status\": \"reading\"}")
if [ "$STATUS" == "403" ]; then
    pass "Test 4.3: Normal user updating admin's item returned 403."
else
    fail "Test 4.3: Expected 403, got $STATUS."
fi

echo "--------------------------------------------------"
echo "📚 5. Metadata Sync (Library Consistency)"
TEST_ISBN="9780141036144"
NEW_TITLE="Nineteen Eighty-Four (Automated Test Edit)"

# Test 5.1: Add item with new Title
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/item/$TEST_ISBN" \
  -H "Authorization: Bearer $NORMAL_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"Title\": \"$NEW_TITLE\"}")

if [ "$STATUS" == "200" ]; then
    pass "Test 5.1: Added item with ISBN $TEST_ISBN and new Title."
else
    fail "Test 5.1: Expected 200, got $STATUS."
fi

# Test 5.2: Update manifestation metadata (Security)
echo "  Checking manifestation update security..."
# No Auth
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/isbn/$TEST_ISBN" \
  -H "Content-Type: application/json" \
  -d "{\"Title\": \"Hacker Title\"}")
if [ "$STATUS" == "401" ]; then
    pass "Test 5.2.1: Anonymous update manifestation returned 401."
else
    fail "Test 5.2.1: Expected 401, got $STATUS."
fi

# Normal User (No write_metadata permission by default)
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/isbn/$TEST_ISBN" \
  -H "Authorization: Bearer $NORMAL_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"Title\": \"Sneaky Title\"}")
if [ "$STATUS" == "403" ]; then
    pass "Test 5.2.2: Normal user update manifestation returned 403."
else
    fail "Test 5.2.2: Expected 403, got $STATUS."
fi

# Test 5.3: Manifestation Update Validation (Pydantic)
echo "  Checking manifestation update validation..."
# Invalid payload (Authors must be list of strings)
RESPONSE=$(curl -s -X POST "$BASE_URL/isbn/$TEST_ISBN" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"Authors\": \"Just a string, not a list\"}")
ERROR=$(echo $RESPONSE | jq -r .error)

if [[ "$ERROR" == "Invalid payload" ]]; then
    pass "Test 5.3.1: Invalid Authors format caught by Pydantic (400)."
else
    fail "Test 5.3.1: Expected 400 'Invalid payload', got '$ERROR'."
fi

# Valid Admin Update
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/isbn/$TEST_ISBN" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"Title\": \"George Orwell - 1984 (Hardened)\", \"Authors\": [\"George Orwell\"]}")
if [ "$STATUS" == "200" ]; then
    pass "Test 5.3.2: Admin update manifestation with valid Pydantic payload returned 200."
else
    fail "Test 5.3.2: Expected 200, got $STATUS."
fi

echo "--------------------------------------------------"
echo "🦖 All tests completed! Me happy! ✨"

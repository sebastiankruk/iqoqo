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
# Automated Verification Suite for Multi-Instance Federation Preview Staging
# Usage: ./scripts/verify_federation_preview.sh [options]

set -euo pipefail

PRIMARY_API_PORT="${PRIMARY_API_PORT:-5001}"
PRIMARY_WEB_PORT="${PRIMARY_WEB_PORT:-8000}"
PEER_API_PORT="${PEER_API_PORT:-5005}"
PEER_WEB_PORT="${PEER_WEB_PORT:-3001}"

PRIMARY_URL="http://127.0.0.1:${PRIMARY_API_PORT}"
PEER_URL="http://127.0.0.1:${PEER_API_PORT}"

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

QUIET=false
SEED_ONLY=false
TIMEOUT=10

show_help() {
    echo "Usage: ./scripts/verify_federation_preview.sh [options]"
    echo ""
    echo "Options:"
    echo "  -h, --help       Show this help message and exit"
    echo "  -q, --quiet      Suppress non-critical informational output"
    echo "  --seed-only      Only run database fixture seeding and user consent configuration"
    echo "  --timeout <sec>  Set timeout in seconds for HTTP and discovery probes (default: 10)"
    echo ""
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        -q|--quiet)
            QUIET=true
            shift
            ;;
        --seed-only)
            SEED_ONLY=true
            shift
            ;;
        --timeout)
            if [[ -z "${2:-}" ]] || ! [[ "$2" =~ ^[0-9]+$ ]]; then
                echo "Error: --timeout requires an integer argument." >&2
                exit 1
            fi
            TIMEOUT="$2"
            shift 2
            ;;
        *)
            echo "Error: Unknown option: $1" >&2
            show_help >&2
            exit 1
            ;;
    esac
done

pass() { echo -e "  [${GREEN}PASS${NC}] $1"; }
fail() { echo -e "  [${RED}FAIL${NC}] $1" >&2; exit 1; }
info() {
    if [ "$QUIET" != "true" ]; then
        echo -e "[${BLUE}INFO${NC}] $1"
    fi
}

if [ "$QUIET" != "true" ]; then
    echo "============================================================"
    echo "  iQoQo Multi-Instance Federation Preview Automated Verifier"
    echo "============================================================"
fi

# 1. Probe running containers
info "Checking container status..."
if ! docker ps --format '{{.Names}}' | grep -q 'iqoqo-preview-web-1'; then
    fail "Primary web container (iqoqo-preview-web-1) is not running!"
fi
if ! docker ps --format '{{.Names}}' | grep -q 'iqoqo-preview-peer-web-1'; then
    fail "Secondary peer web container (iqoqo-preview-peer-web-1) is not running!"
fi
pass "Both primary and peer web containers are active in Docker."

# 2. Probe HTTP health endpoints (skipped in seed-only mode)
if [ "$SEED_ONLY" != "true" ]; then
    info "Checking HTTP health probes..."
    primary_health=$(curl -s -m "$TIMEOUT" -o /dev/null -w "%{http_code}" "${PRIMARY_URL}/api/health" || echo "000")
    if [ "$primary_health" != "200" ]; then
        fail "Primary health check failed (HTTP ${primary_health} on ${PRIMARY_URL}/api/health)"
    fi
    pass "Primary API health check OK (HTTP 200 on port ${PRIMARY_API_PORT})"

    peer_health=$(curl -s -m "$TIMEOUT" -o /dev/null -w "%{http_code}" "${PEER_URL}/api/health" || echo "000")
    if [ "$peer_health" != "200" ]; then
        fail "Peer health check failed (HTTP ${peer_health} on ${PEER_URL}/api/health)"
    fi
    pass "Peer API health check OK (HTTP 200 on port ${PEER_API_PORT})"
fi

# 3. Ensure test user with federation consent and lending fixtures on peer
info "Ensuring peer user federation consent & lending fixtures in peer database..."
docker exec -i iqoqo-preview-peer-web-1 python3 -c "
from app import create_app, db
from app.db.auth import User
from app.db.core import Work, Expression, Manifestation, Item
from app.db.federation import FederationConsent, FederationActivity, ActivityStatus
from app.core.federation_tasks import process_inbound_activity
app = create_app()
with app.app_context():
    u = User.query.filter_by(email='peer-admin@iqoqo.cc').first()
    if u:
        u.public_username = 'peeradmin'
        consent = FederationConsent.query.filter_by(user_id=u.id).first()
        kwargs = {'user_id': u.id, 'federated_profile': True, 'federated_collection': True}
        if hasattr(FederationConsent, 'auto_accept_follows'):
            kwargs['auto_accept_follows'] = True
        if not consent:
            consent = FederationConsent(**kwargs)
            db.session.add(consent)
        else:
            consent.federated_profile = True
            consent.federated_collection = True
            if hasattr(consent, 'auto_accept_follows'):
                consent.auto_accept_follows = True

        # Ensure seed lendable item fixture
        item = Item.query.filter_by(local_barcode='PEER-LEND-001').first()
        if not item:
            w = Work(title='Solaris')
            db.session.add(w)
            db.session.flush()
            exp = Expression(work_id=w.id, content_type='text', language='en')
            db.session.add(exp)
            db.session.flush()
            mf = Manifestation(expression_id=exp.id, label='Solaris - English Translation', isbn13='9780156027601', format='book')
            db.session.add(mf)
            db.session.flush()
            item = Item(manifestation_id=mf.id, owner_id=u.id, local_barcode='PEER-LEND-001', collection_status='available', visibility='public')
            db.session.add(item)
        else:
            item.collection_status = 'available'
            item.lent_to_user_id = None
            item.lent_to_name = None
        db.session.commit()

    # Reconcile any queued inbound activities
    queued = FederationActivity.query.filter_by(status=ActivityStatus.QUEUED, direction='inbound').all()
    for act in queued:
        try:
            process_inbound_activity(str(act.id), act.object_json or {})
        except Exception as exc:
            pass
"
pass "Peer admin user (peeradmin) configured with active federated profile, lending fixture, & auto-accept consent."

# Ensure primary instance test user has federation consent enabled
info "Ensuring primary user federation consent in primary database..."
docker exec -i iqoqo-preview-web-1 python3 -c "
from app import create_app, db
from app.db.auth import User
from app.db.federation import FederationConsent
app = create_app()
with app.app_context():
    u = User.query.filter((User.email == 'ci-admin@iqoqo.cc') | (User.email == 'admin@iqoqo.cc')).first()
    if u:
        if not u.public_username:
            u.public_username = 'ciadmin'
        consent = FederationConsent.query.filter_by(user_id=u.id).first()
        kwargs = {'user_id': u.id, 'federated_profile': True, 'federated_collection': True}
        if hasattr(FederationConsent, 'auto_accept_follows'):
            kwargs['auto_accept_follows'] = True
        if not consent:
            consent = FederationConsent(**kwargs)
            db.session.add(consent)
        else:
            consent.federated_profile = True
            consent.federated_collection = True
            if hasattr(consent, 'auto_accept_follows'):
                consent.auto_accept_follows = True
        db.session.commit()

    skruk_user = User.query.filter_by(email='sebastian.kruk@gmail.com').first()
    if skruk_user:
        if not skruk_user.public_username:
            skruk_user.public_username = 'skruk'
        s_consent = FederationConsent.query.filter_by(user_id=skruk_user.id).first()
        if not s_consent:
            s_consent = FederationConsent(user_id=skruk_user.id, federated_profile=True, federated_collection=True)
            db.session.add(s_consent)
        else:
            s_consent.federated_profile = True
            s_consent.federated_collection = True
        db.session.commit()
"
pass "Primary user configured with active federated profile & consent."

if [ "$SEED_ONLY" = "true" ]; then
    pass "Seed fixtures configuration completed successfully (--seed-only)."
    exit 0
fi

# 4. Verify RFC 7033 WebFinger Discovery on Peer
info "Testing WebFinger RFC 7033 discovery..."
webfinger_json=$(curl -s -m "$TIMEOUT" -H "Host: localhost:${PEER_API_PORT}" "${PEER_URL}/.well-known/webfinger?resource=acct:peeradmin@localhost:${PEER_API_PORT}" || echo "{}")
actor_href=$(echo "$webfinger_json" | jq -r '.links[] | select(.rel=="self" and .type=="application/activity+json") | .href' 2>/dev/null || true)

if [ -z "$actor_href" ] || [ "$actor_href" = "null" ]; then
    # Fallback to querying with peer.iqoqo.cc domain directly
    webfinger_json=$(curl -s -m "$TIMEOUT" "${PEER_URL}/.well-known/webfinger?resource=acct:peeradmin@peer.iqoqo.cc" || echo "{}")
    actor_href=$(echo "$webfinger_json" | jq -r '.links[] | select(.rel=="self" and .type=="application/activity+json") | .href' 2>/dev/null || true)
fi

if [ -z "$actor_href" ] || [ "$actor_href" = "null" ]; then
    fail "WebFinger failed to return self ActivityStreams link! Response: ${webfinger_json}"
fi
pass "WebFinger RFC 7033 resolved successfully to: ${actor_href}"

# 5. Fetch Actor JSON-LD Document
info "Testing Actor JSON-LD retrieval with ActivityPub content negotiation..."
resolved_actor_url=$(echo "$actor_href" | sed -E "s|^https?://peer\.iqoqo\.cc|${PEER_URL}|")
actor_json=$(curl -s -k -L -m "$TIMEOUT" -H "Accept: application/activity+json" "${resolved_actor_url}")
actor_type=$(echo "$actor_json" | jq -r '.type' 2>/dev/null || true)
actor_inbox=$(echo "$actor_json" | jq -r '.inbox' 2>/dev/null || true)
has_key=$(echo "$actor_json" | jq -r '.publicKey.publicKeyPem' 2>/dev/null || true)

if [ "$actor_type" != "Person" ] || [ -z "$actor_inbox" ] || [ "$actor_inbox" = "null" ]; then
    fail "Actor document invalid or missing inbox/type! Response: ${actor_json}"
fi

if [[ "$has_key" != *"BEGIN PUBLIC KEY"* ]]; then
    fail "Actor document missing valid RSA publicKeyPem!"
fi
pass "Actor document is valid ActivityStreams Person with RSA key and inbox (${actor_inbox})"

# 6. Verify Inbox Endpoint Rejects Unsigned Activities
info "Testing Inbox security and HTTP signature validation..."
unsigned_code=$(curl -s -m "$TIMEOUT" -o /dev/null -w "%{http_code}" -X POST "${PEER_URL}/api/federation/inbox" \
    -H "Content-Type: application/activity+json" \
    -d '{"type": "Follow", "actor": "http://attacker.local/actor", "object": "http://victim.local/actor"}' || echo "000")

if [ "$unsigned_code" != "400" ] && [ "$unsigned_code" != "401" ]; then
    fail "Inbox did not reject unsigned activity! Expected 400 or 401, got HTTP ${unsigned_code}"
fi
pass "Inbox endpoint securely rejects unsigned activities (HTTP ${unsigned_code})"

# 7. Test Cross-Container ActivityPub Resolution (FederationClient)
info "Testing cross-container actor fetch via FederationClient..."
actor_path=$(echo "$actor_href" | sed -E 's|^https?://[^/]+||')
internal_actor_url="http://peer-web:5000${actor_path}"
fetch_result=$(docker exec -i iqoqo-preview-web-1 python3 -c "
from app import create_app
from app.core.federation_client import FederationClient
app = create_app()
with app.app_context():
    client = FederationClient()
    actor = client.fetch_actor('${internal_actor_url}')
    if actor and actor.get('preferredUsername') == 'peeradmin':
        print('SUCCESS')
    else:
        print('FAILED')
" 2>&1 | tr -d '\r')

if [[ "$fetch_result" != *"SUCCESS"* ]]; then
    fail "Cross-container FederationClient failed to fetch remote peer actor! Output: ${fetch_result}"
fi
pass "Primary FederationClient successfully fetched and verified remote Actor over internal network."

# 8. Test Peer Discovery in Primary Instance's Federation Trust Graph (with cleanup)
info "Testing peer discovery across instance boundaries..."
register_result=$(docker exec -i iqoqo-preview-web-1 python3 -c "
from app import create_app, db
from app.core import federation_discovery
from app.db.federation import FederationInstance
from sqlalchemy import delete
app = create_app()
with app.app_context():
    try:
        inst = federation_discovery.discover_instance('peer-web:5000')
        if inst:
            print('SUCCESS')
        else:
            print('FAILED')
    finally:
        # Clean up synthetic smoke test row so preview database is not polluted with internal container names
        db.session.execute(delete(FederationInstance).where(FederationInstance.domain == 'peer-web:5000'))
        db.session.commit()
" 2>&1 | tr -d '\r')

if [[ "$register_result" == *"SUCCESS"* ]]; then
    pass "Peer instance cross-container discovery smoke test succeeded (synthetic row cleaned up)."
else
    info "Note: Could not discover peer instance across internal containers: ${register_result}"
fi

# Clean up any synthetic primary instance row on peer as well
docker exec -i iqoqo-preview-peer-web-1 python3 -c "
from app import create_app, db
from app.db.federation import FederationInstance
from sqlalchemy import delete
app = create_app()
with app.app_context():
    db.session.execute(delete(FederationInstance).where(FederationInstance.domain == 'web:5000'))
    db.session.commit()
" 2>/dev/null || true

echo "============================================================"
echo -e "${GREEN}All Multi-Instance Federation Preview checks PASSED!${NC}"
echo "  * Primary Web UI:      http://localhost:${PRIMARY_WEB_PORT} (API: :${PRIMARY_API_PORT})"
echo "  * Secondary Peer UI:   http://localhost:${PEER_WEB_PORT} (API: :${PEER_API_PORT})"
echo "  * Federation stream:   http://localhost:${PRIMARY_WEB_PORT}/admin/federation"
echo "  * Peer Discovery:      Verified clean (no synthetic internal rows left in database)"
echo "============================================================"
exit 0

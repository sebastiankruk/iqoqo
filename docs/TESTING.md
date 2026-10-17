# iqoqo Testing Strategy & Federation Verification Guide

This document details the test architecture of the iqoqo ecosystem, including unit, integration, end-to-end, and multi-instance federation testing workflows.

## 1. Testing Architecture Overview

The iqoqo platform requires strict test coverage across multiple tiers:

| Tier | Tooling | Command | Scope |
| :--- | :--- | :--- | :--- |
| **Backend Layer** | `pytest` | `make test-backend` | FRBR ontology mapping, SQLAlchemy models, API endpoints, serialization |
| **Frontend Layer** | `Vitest` + React Testing Library | `make test-frontend` | Components, custom React hooks, layout boundaries, user interactions |
| **End-to-End (E2E)** | `Playwright` | `make test-e2e` | Multi-page browser workflows, authentication exchange, multi-instance federation |
| **Operational Scripts** | `pytest` + `bats` | `make test-scripts-python` | Deployment, database management, and maintenance automation scripts |

---

## 2. Multi-Instance Federation E2E Testing

With ActivityPub server-to-server federation introduced in `v0.9.0`, testing requires verifying communications between two isolated instance origins (Instance Alpha and Instance Beta) with separate databases, cryptographic identities, and session states.

### 2.1 Automated Playwright Multi-Instance Suite

The automated multi-instance test suite lives in:

```bash
frontend/__tests__/e2e/federation_multi_instance.spec.ts
```

The suite validates:

1. **RFC 7033 WebFinger Discovery**: Resolving `/.well-known/webfinger` queries for user identities and retrieving `application/jrd+json` descriptors.
2. **Actor JSON-LD Resolution**: Fetching Person Actor representations with cryptographic `publicKeyPem` and inbox URLs.
3. **Dual Browser Context Isolation**: Simulating distinct user personas in independent browser contexts (`contextA` and `contextB`) to verify session cookie and storage separation.
4. **Signed ActivityPub Delivery**: Dispatching signed `Follow` activities and verifying inbound processing on recipient inboxes while rejecting unsigned or forged requests.

To run the automated suite:

```bash
cd frontend && npx playwright test __tests__/e2e/federation_multi_instance.spec.ts
```

---

## 3. Local Peer Test Backend Helper

To test federation locally without running full Docker Compose clusters, use the peer launcher script:

```bash
python scripts/launch_federation_peer.py --port 5003
```

### Options

- `--port`: The local port to bind the peer backend (default: `5003`).
- `--base-url`: The public or local URL of the peer instance (default: `http://127.0.0.1:<port>`).
- `--db-url`: SQLite or PostgreSQL database URL for isolated peer storage (default: `sqlite:////tmp/iqoqo_federation_peer_test.db`).
- `--peer-username`: Username of the pre-seeded federated user (default: `bob`).
- `--seed-only`: Initialize tables and seed the peer user, then exit immediately.
- `--check-ready`: Poll `/api/health` until the peer backend responds.

### Example: Quick Seed and Verification

```bash
# Initialize isolated peer database with test user
.venv/bin/python scripts/launch_federation_peer.py --seed-only --port 5003

# Verify WebFinger resolution on peer instance
curl -s "http://127.0.0.1:5003/.well-known/webfinger?resource=acct:bob@127.0.0.1:5003" | jq .
```

---

## 4. Staging Dual-Instance Preview Walkthrough

For staging environments and manual operator inspection, Docker Compose provides a paired preview stack.

### 4.1 Launching the Paired Preview Stack

To start both the primary preview instance and the secondary peer instance:

```bash
make preview-up FEDERATION_PAIR=1
```

Or using the `iqopretest` pre-flight runner:

```bash
iqopretest --federation-pair
```

Clone parameters can be overridden via environment variables or CLI flags if syncing from a specific host:

```bash
# Override clone host and locations
iqopretest --src-host other.host.net --src-loc /opt/iqoqo --federation-pair

# Or skip cloning to test against existing local preview state
iqopretest --skip-clone --federation-pair
```

This starts:

- **Primary Instance**:
  - Web UI: `http://localhost:8000` (or configured `NGINX_PORT`)
  - Flask API: `http://localhost:5000`
- **Secondary Peer Instance** (`docker-compose.federation-preview.yml`):
  - Web UI: `http://localhost:3001` (Peer Frontend)
  - Flask API: `http://localhost:5001` (Peer Backend)
  - Dedicated PostgreSQL database: `peer-db` (`iqoqo_peer`)

### 4.2 Step-by-Step Manual Inspection

1. **Verify Primary and Secondary Health**:

   ```bash
   curl -I http://localhost:8000/api/health
   curl -I http://localhost:5001/api/health
   ```

2. **Verify Cross-Instance WebFinger Discovery**:
   Query the peer instance's WebFinger endpoint:

   ```bash
   curl -s "http://localhost:5001/.well-known/webfinger?resource=acct:peer-admin@iqoqo.cc" | jq .
   ```

   Confirm the returned JSON contains a `self` link with `type: "application/activity+json"`.

3. **Verify Actor JSON-LD Profile**:
   Fetch the resolved Actor URI with the ActivityPub accept header:

   ```bash
   curl -s -H "Accept: application/activity+json" http://localhost:5001/api/federation/actor/peer-admin | jq .
   ```

   Ensure `publicKey` and `inbox` fields are populated.

4. **Verify Activity Logs in Admin UI**:
   - Navigate to `http://localhost:8000/admin` on the primary instance.
   - Open **Federation Management** to review trusted peer instances (`/admin/federation`).
   - Check the **Activity Stream** tab to observe inbound and outbound federated activities in real time.

5. **Teardown**:
   When inspection is complete, stop the preview stack cleanly:

   ```bash
   make preview-down
   ```

## Context

Testing server-to-server ActivityPub federation requires two communicating HTTP origins. While Python unit tests (`tests/test_federation_e2e.py`) simulate HTTP request loops via mock adapters, browser-level interaction, CORS handling, cookie isolation, and client-side notifications require real multi-origin browser testing.

## Goals / Non-Goals

**Goals:**
- Provide a Playwright E2E test suite running across dual origin configurations.
- Provide a simple Docker Compose profile / Makefile option for staging dual-instance manual inspection.

**Non-Goals:**
- Maintaining an external public testnet instance permanently.

## Decisions

### 1. Dedicated Compose Profile for Federation Preview
- **Decision:** Introduce a lightweight overlay `docker-compose.federation-preview.yml` spinning up a secondary peer backend (`iqoqo-peer-backend`) and database on alternative ports (e.g. 5001 / 3001) linked via an internal Docker bridge.
- **Rationale:** Keeps standard preview deployments lightweight while making dual-instance preview one command away.

### 2. Multi-Context Playwright Browser Harness
- **Decision:** In Playwright tests, utilize two independent `BrowserContext` instances (`contextA` and `contextB`) with isolated cookies and storage state to simulate User A on Instance A and User B on Instance B.
- **Rationale:** Matches real multi-user federation interactions without cookie collisions.

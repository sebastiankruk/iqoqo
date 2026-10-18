## Why

With server-to-server federation foundation deployed in `v0.9.0` and `v0.9.1`, end-to-end multi-instance verification is currently restricted to Python mock test clients (`tests/test_federation_e2e.py`). To guarantee rock-solid federation in real browser environments and during staging preview deployments:
1. Playwright end-to-end tests (`make test-e2e`) must test cross-instance flows between multiple running server instances (Instance A and Instance B) to validate Actor discovery, follow requests, and activity propagation directly through the web UI and reverse proxies.
2. Manual federation testing must be accessible on staging environments (such as preview environments spawned via `iqopretest` or `make preview-up`), allowing developers to launch two isolated peer instances on separate ports/subdomains with pre-seeded test keys and mutual trust settings.

## What Changes

- Add a multi-instance Playwright test suite (`frontend/__tests__/e2e/federation_multi_instance.spec.ts`) configured to exercise federation interactions across two test instance origins.
- Extend orchestration in `Makefile` and `docker-compose.preview.yml` (or dedicated federation compose overlay `docker-compose.federation-preview.yml`) to support launching dual paired instances (`--federation-pair`) for manual end-to-end inspection in `iqopretest`.
- Automate instance pairing configuration (e.g. pre-configuring `FEDERATION_BASE_URL`, mutual trust level, and dummy peer keys) for rapid manual federation verification.

## Capabilities

### New Capabilities
- `federation-multi-instance-e2e`: Automated Playwright multi-instance federation test execution.
- `preview-federation-sandbox`: Orchestrated dual-instance preview testing environment for manual federation inspection.

## Impact

- Affects `Makefile`, `docker-compose.preview.yml` / new overlay, and `frontend/__tests__/e2e/`.
- Zero production runtime overhead; purely test harness and staging orchestration.

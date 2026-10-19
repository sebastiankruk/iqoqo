## 1. Discovery Endpoints & Nginx Configuration

- [x] Create `app/api/federation.py` with WebFinger, NodeInfo 2.1, and Actor endpoints.
- [x] Create `app/api/federation_guard.py` with `@federation_required`.
- [x] Update `deploy/nginx.conf` and `deploy/nginx.conf.example` with `/.well-known/` proxy blocks.
- [x] Write tests in `tests/test_federation_discovery.py`.

## 2. HTTP Signatures & SSRF-Safe FederationClient

- [x] Implement `app/core/http_signatures.py` with `sign_request` and `verify_request`.
- [x] Implement `app/core/federation_client.py` using `app/utils/http_client.py`.
- [x] Write tests in `tests/test_http_signatures.py` and `tests/test_federation_ssrf.py`.


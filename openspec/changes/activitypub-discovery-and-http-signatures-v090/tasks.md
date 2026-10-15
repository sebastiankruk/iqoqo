## 1. Discovery Endpoints & Nginx Configuration

- [ ] Create `app/api/federation.py` with WebFinger, NodeInfo 2.1, and Actor endpoints.
- [ ] Create `app/api/federation_guard.py` with `@federation_required`.
- [ ] Update `deploy/nginx.conf` and `deploy/nginx.conf.example` with `/.well-known/` proxy blocks.
- [ ] Write tests in `tests/test_federation_discovery.py`.

## 2. HTTP Signatures & SSRF-Safe FederationClient

- [ ] Implement `app/core/http_signatures.py` with `sign_request` and `verify_request`.
- [ ] Implement `app/core/federation_client.py` using `app/utils/http_client.py`.
- [ ] Write tests in `tests/test_http_signatures.py` and `tests/test_federation_ssrf.py`.


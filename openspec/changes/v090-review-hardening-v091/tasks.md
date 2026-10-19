## 1. Cryptographic Verification & Transport Resilience

- [ ] 1.1 Implement actor public key re-fetching on verification failure in `app/core/http_signatures.py` and verify with unit tests in `tests/test_http_signatures.py`
- [ ] 1.2 Add exponential backoff retry via `tenacity` and timeouts `(10, 30)` in `FederationClient.post_to_inbox` in `app/core/federation_client.py` and verify with mocked network tests in `tests/test_federation_e2e.py`
- [ ] 1.3 Unify `FEDERATION_BASE_URL` resolution across `app/config.py`, `app/api/profile.py`, and `app/api/federation.py` and verify base URL consistency tests

## 2. Fediverse Discovery & Identity Hygiene

- [ ] 2.1 Enforce strict domain match in `_handle_webfinger_lookup` and link to `/u/{username}` canonical profile, apply `@limiter.limit("10 per minute")` to `POST /api/federation/follow`, remove `":" in domain` from scheme check, and sanitize 500 error message in `federation_follow_remote` in `app/api/federation.py`, verifying with `tests/test_federation_discovery.py`
- [ ] 2.2 Shift on-demand RSA-2048 keypair generation out of unauthenticated `GET /api/federation/actor/u/<uuid>` into consent opt-in in `app/api/profile.py`

## 3. Database Schema Integrity & Migrations

- [ ] 3.1 Add composite unique constraint `uq_federation_followers_pair` on `FederationFollower(local_user_id, remote_actor_id)` in `app/db/federation.py` and generate linear Alembic migration
- [ ] 3.2 Synchronize Alembic migration for `check_user_default_item_visibility` check constraint with `User` model in `app/db/auth.py`

## 4. FRBR Merges & Exemplar Barcode Scanner

- [ ] 4.1 Implement multi-hop recursive tombstone resolution in `app/core/frbr_merge.py` and `app/api/public_rdf.py`, verifying chained merges in `tests/test_frbr_merge_tombstones.py`
- [ ] 4.2 Support `Item.local_barcode` lookup in `app/api/scanner.py` and verify scanning exemplar tags in `tests/test_item_local_barcode.py`

## 5. Frontend i18n & E2E Live-Instance Testing

- [ ] 5.1 Extract hardcoded English strings into `en.json` and `pl.json` for `ProfilePage`, `FederationConsentSettings`, and `EditItemDialog` and verify translation completeness
- [ ] 5.2 Update multi-instance Playwright test `frontend/__tests__/e2e/federation_multi_instance.spec.ts` to exercise secondary peer container instead of mocked route fulfillment

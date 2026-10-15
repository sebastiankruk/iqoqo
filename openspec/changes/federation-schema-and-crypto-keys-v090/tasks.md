## 1. Database Models & Alembic Migration

- [ ] Create `app/db/federation.py` defining FederationInstance, FederationActor, FederationFollower, FederationActivity, and FederationConsent.
- [ ] Add key columns to `User` in `app/db/auth.py`.
- [ ] Create linear Alembic migration `v0_9_0_federation_schema`.
- [ ] Register cascading deletes/cleanup in `app/core/account_lifecycle.py` and `app/core/frbr_merge.py`.

## 2. RSA Keypair Management & Fernet Encryption

- [ ] Implement `app/core/federation_keys.py` with `generate_actor_keypair`, `get_actor_private_key`, `get_actor_public_key`.
- [ ] Implement Fernet encryption/decryption of private key PEM using `SECRET_KEY`.
- [ ] Write test suite in `tests/test_federation_models_and_keys.py`.


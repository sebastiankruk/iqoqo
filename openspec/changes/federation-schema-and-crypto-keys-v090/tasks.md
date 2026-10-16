## 1. Database Models & Alembic Migration

- [x] Create `app/db/federation.py` defining FederationInstance, FederationActor, FederationFollower, FederationActivity, and FederationConsent.
- [x] Add key columns to `User` in `app/db/auth.py`.
- [x] Create linear Alembic migration `v0_9_0_federation_schema`.
- [x] Register cascading deletes/cleanup in `app/core/account_lifecycle.py` and `app/core/frbr_merge.py`.

## 2. RSA Keypair Management & Fernet Encryption

- [x] Implement `app/core/federation_keys.py` with `generate_actor_keypair`, `get_actor_private_key`, `get_actor_public_key`.
- [x] Implement Fernet encryption/decryption of private key PEM using `SECRET_KEY`.
- [x] Write test suite in `tests/test_federation_models_and_keys.py`.


## Why
ActivityPub server-to-server federation requires database models to track remote instances, cached actors, follow relationships, activities, and cryptographic signing keys for local actors.
## What Changes

- Create `app/db/federation.py` with models: `FederationInstance`, `FederationActor`, `FederationFollower`, `FederationActivity`, and `FederationConsent`.
- Add `federation_key_id` and `federation_public_key` columns to `User` in `app/db/auth.py`.
- Generate linear Alembic migration for the `federation` schema.
- Implement RSA-2048 keypair generation and Fernet encryption at rest in `app/core/federation_keys.py`.
- Register federation foreign keys in `app/core/frbr_merge.py` and `app/core/account_lifecycle.py`.

## Capabilities

### New Capabilities
- `federation-schema-and-keys`: PostgreSQL federation schema models, Alembic migrations, and Fernet-encrypted RSA-2048 keypair lifecycle

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

Database schema addition, new core key management service, and User model extension.

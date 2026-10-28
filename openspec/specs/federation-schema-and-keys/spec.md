# federation-schema-and-keys Specification

## Purpose
PostgreSQL federation schema models, Alembic migrations, and Fernet-encrypted RSA-2048 keypair lifecycle.

## Requirements

### Requirement: Federation Schema Isolation

The database SHALL isolate federation entities within a dedicated 'federation' PostgreSQL schema.

#### Scenario: Migration creates schema and tables

- **WHEN** Alembic migration runs upgrade
- **THEN** Schema 'federation' and tables FederationInstance, FederationActor, FederationFollower, FederationActivity, FederationConsent are created.

### Requirement: Encrypted RSA Actor Key Lifecycle

The system SHALL generate RSA-2048 keypairs for users opting into federation and encrypt private keys at rest using SECRET_KEY-derived Fernet.

#### Scenario: Keypair generation and encryption

- **WHEN** A user opts into federation consent
- **THEN** A 2048-bit RSA keypair is generated, the public key is stored in PEM format, and the private key is stored Fernet-encrypted.

### Requirement: Key File Permissions & Host Isolation

The system SHALL enforce restrictive permissions on cryptographic key storage, maintaining `0700` on the key directory and `0600` on private key PEM files.

#### Scenario: Operational scripts preserve key file permissions

- **WHEN** Container startup or pre-deploy scripts execute
- **THEN** Key directories are excluded from recursive world-writable permissions and private keys remain unreadable to unauthorized users.

### Requirement: State-Mutating Key Generation Restriction

The system SHALL only generate actor keypairs during explicit, authenticated state mutations and never during read-only `GET` actor requests.

#### Scenario: Unauthenticated GET does not generate keys

- **WHEN** A client issues `GET /api/federation/actor/u/<uuid>` for an unconsented user or a user without keys
- **THEN** The system returns 404 Not Found without creating key files or committing database rows.

### Requirement: Follower Relation Unique Constraint
The database SHALL enforce a composite unique constraint on `FederationFollower(local_user_id, remote_actor_id)` to prevent race conditions and duplicate follower records.

#### Scenario: Duplicate follow delivery does not create duplicate follower row

- **WHEN** concurrent or duplicate Follow activities for the same target user and remote actor are processed
- **THEN** the database enforces uniqueness without creating duplicate rows in `federation.followers`.

### Requirement: User Visibility Check Constraint Migration
The Alembic migration lineage SHALL include explicit database-level check constraints enforcing permitted values for `default_item_visibility`.

#### Scenario: Migration enforces permitted visibility values

- **WHEN** database migrations are executed
- **THEN** a check constraint ensures `default_item_visibility` is either 'private' or 'public'.

### Requirement: Fail-Closed Key Encryption Secret and Explicit Instance Actor Key Provisioning

Cryptographic actor key encryption SHALL fail closed with an explicit runtime error whenever `SECRET_KEY` is unconfigured rather than falling back to a static placeholder secret, and the instance-level actor keypair (`server.pem`) SHALL be provisioned idempotently during deployment bootstrap or explicit authenticated admin `POST` operations while remaining persistent across container restarts.

#### Scenario: Missing SECRET_KEY aborts key encryption without fallback secret

- **WHEN** actor key encryption or decryption is invoked in an environment where `SECRET_KEY` is missing or empty
- **THEN** the key manager raises `RuntimeError` immediately and never derives a Fernet key from a hardcoded fallback string

#### Scenario: Bootstrap initializes instance actor key idempotently while GET remains side-effect free

- **WHEN** deployment initialization (`init_auth.py`) runs with a valid `SECRET_KEY`
- **THEN** the system provisions the Fernet-encrypted `server.pem` RSA-2048 keypair (`0700` directory, `0600` key file) if absent, whereas read-only `GET` requests (`GET /api/federation/actor`, `GET /api/v1/admin/federation/key-fingerprint`) never generate keys on disk

#### Scenario: Peer preview stack retains cryptographic keys across container recreation

- **WHEN** `peer-migration` initializes keys and `peer-web` is restarted or recreated in the federation preview stack
- **THEN** both services share a persistent data volume so `server.pem` and user actor keys remain intact

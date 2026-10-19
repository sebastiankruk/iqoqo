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

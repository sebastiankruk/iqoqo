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

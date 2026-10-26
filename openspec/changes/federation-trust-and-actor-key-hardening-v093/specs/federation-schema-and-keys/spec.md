## ADDED Requirements

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

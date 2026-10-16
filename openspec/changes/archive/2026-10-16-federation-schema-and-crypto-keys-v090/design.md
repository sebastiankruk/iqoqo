## Context

Cherry-picked from `feat/0.9.0-federation` branch and hardened with Fernet encryption per v0.8.3 architectural security guidelines.

## Goals / Non-Goals

**Goals:**
- Establish relational foundation for ActivityPub protocol.
- Secure cryptographic key storage preventing cleartext PEM leaks in DB dumps or disk.

**Non-Goals:**
- Hardware security module (HSM) key storage.
- Inbound/outbound HTTP processing (handled in C74/C76).

## Decisions

### Fernet Symmetric Encryption at Rest
* **Decision**: Private keys are encrypted with Fernet keyed from `SECRET_KEY` via `app/core/config_service.py`.
* **Rationale**: Prevents cleartext key exposure in database backups.

### PostgreSQL Schema Separation
* **Decision**: Federation tables live in `schema='federation'` matching existing `auth`, `catalog`, and `inventory` schema separation.
* **Rationale**: Maintain architectural cleanliness.

## Risks / Trade-offs

- ('[Risk] SQLite compatibility during test suites', 'Mitigation: Ensure SQLAlchemy models gracefully fallback when schemas are not supported on SQLite.')

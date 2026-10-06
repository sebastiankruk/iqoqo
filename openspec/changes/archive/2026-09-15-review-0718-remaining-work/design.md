## Context

This change executes the Pre-0.8.0 hardening strategy detailed in the proposal. It involves migrating sensitive API credentials to the database and applying targeted security and operational patches to the backend.

## Goals / Non-Goals

**Goals:**
- Securely store and retrieve external API credentials using the database, maintaining encryption at rest.
- Block potential brute-force and enumeration vectors on public-facing API routes.
- Prevent XSS and SSRF in social and metadata fetching endpoints.

**Non-Goals:**
- Any refactoring of the FRBR domain models, routing, or frontend state management (reserved for the 0.8.0 milestone).

## Decisions

- **Fernet Encryption for InstanceSettings**: External API keys will be encrypted using Python's `cryptography.fernet` symmetric encryption, with the key derived deterministically from the Flask `SECRET_KEY`. This ensures that even a full database dump does not compromise third-party API credentials unless the `.env` `SECRET_KEY` is also compromised.
- **ConfigService Blocklist**: `app/core/config_service.py` will implement a strict blocklist for "Boot keys" (`SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`) ensuring they are only ever read from `.env` and never from the database.
- **XSS Prevention via Bleach**: The naive regex used for sanitizing social feedback will be replaced with `bleach.clean()` to reliably strip HTML without trusting arbitrary regex edge-cases.
- **Flask-Limiter for Abuse Prevention**: Endpoints like `/api/profile/search` and public RSS feeds will receive `@limiter.limit` decorators to prevent enumeration and DB exhaustion.

## Risks / Trade-offs

- **Risk:** Complete database lock-out if `SECRET_KEY` is lost.
  - **Mitigation:** Emphasize in deployment documentation that `SECRET_KEY` is the master key for all encrypted database credentials.
- **Risk:** Migration from `.env` could break local development environments if they aren't bootstrapped.
  - **Mitigation:** The `.env.example` will clearly document the shift, and the admin UI will provide a seamless way to enter these keys post-deployment.

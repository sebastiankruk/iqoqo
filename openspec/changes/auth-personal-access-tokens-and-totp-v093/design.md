## Context

Delivers roadmap items 'Enable OTP authentication' and 'Personal Access Tokens'.

## Goals / Non-Goals

**Goals:**
- Secure external automation and enforce high-privilege account security.

**Non-Goals:**
- WebAuthn / FIDO2 hardware keys (deferred to v1.1+).

## Decisions

### One-Way Token Hashing
* **Decision**: Store only SHA-256 hash of PAT; show plaintext token once on generation.
* **Rationale**: Prevents token exposure in database compromise.

### Prefixed Identifiers
* **Decision**: All PATs start with `iqo_` prefix.
* **Rationale**: Enables instant regex identification by secret scanners like Gitleaks.

## Risks / Trade-offs

- ('[Risk] User loses TOTP device and gets locked out', 'Mitigation: Generate 8 single-use recovery codes during enrollment.')

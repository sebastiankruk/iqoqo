## ADDED Requirements

### Requirement: Monitoring infrastructure credentials under secret management policy
The system SHALL treat monitoring infrastructure credentials (OpenObserve root password, OTEL collector auth tokens) with the same security posture as application-level API keys: they MUST NOT appear as plaintext literals in version-controlled files and MUST be sourced exclusively from auto-generated ephemeral secrets, environment variables, or encrypted configuration stores.

#### Scenario: Auditing all credential sources
- **WHEN** a security auditor enumerates all credential sources in the repository
- **THEN** monitoring credentials (OpenObserve, OTEL) are managed identically to application secrets — auto-generated at runtime and stored in DB/cache or sourced from `.env`, never from hardcoded fallbacks in scripts, configs, or documentation

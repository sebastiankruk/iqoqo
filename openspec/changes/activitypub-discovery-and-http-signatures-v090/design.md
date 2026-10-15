## Context

Adapts Phase 2 & 3 of federation roadmap to v0.8.4 SSRF socket pinning architecture.

## Goals / Non-Goals

**Goals:**
- Achieve interoperability with Mastodon and BookWyrm discovery.
- Prevent SSRF and replay attacks on server-to-server communications.

**Non-Goals:**
- Inbound activity handling (handled in C76).

## Decisions

### Draft-cavage-12 Standard
* **Decision**: Use `draft-cavage-http-signatures-12` signing `(request-target)`, `host`, `date`, and `digest`.
* **Rationale**: Industry standard for Fediverse interoperability.

### SSRF Pinning
* **Decision**: Route all outbound HTTP requests through `app/utils/http_client.py` `safe_get` / `safe_post`.
* **Rationale**: Eliminates DNS rebinding and internal network probing.

## Risks / Trade-offs

- ('[Risk] Clock drift on self-hosted instances', 'Mitigation: Allow +/-300s window and log NTP sync warnings.')

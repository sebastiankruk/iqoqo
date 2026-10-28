## Why
Establishes the final, machine-readable API contract required for the v1.0.0 Capacitor mobile apps and enables collector AI interaction via Gemini Custom Gems.
## What Changes

- Upgrade `app/api/docs.py` to emit OpenAPI 3.1 covering 100% of routes (catalog, items, wishlist, SPARQL, notifications, auth, federation).
- Add CI contract testing verifying route decorators against emitted OpenAPI schema.
- Deliver `.agents/skills/federation-interop-tester/SKILL.md` and `.agents/skills/openapi-contract-auditor/SKILL.md`.
- Publish collector Gemini Gem template and OpenAPI Action spec in `docs/gems/iqoqo-librarian-gem.md`.

## Capabilities

### New Capabilities
- `openapi-31-contract-and-ai-skills`: Complete 100% OpenAPI 3.1 specification, contract testing CI gate, AI skills, and collector Gemini Gem template

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

Completes API documentation and adds agent skills and user-facing AI templates.

## Why
Production domain migration to `iqoqo.kruk.cc` requires configuration updates; Cloudflare WAF rules must be configured to prevent Bot Fight Mode from blocking Semantic Web and ActivityPub agents.
## What Changes

- Update deployment configs, `.env.example`, and OTel collector CORS origins for `iqoqo.kruk.cc`.
- Support WebFinger resource domain aliasing (`FEDERATION_BASE_URL` vs. host domain).
- Codify Cloudflare rules (`deploy/cloudflare-semantic-federation-rules.md` and setup script) allowing unchallenged access to `/.well-known/*`, `/api/federation/*`, and semantic MIME types (`application/activity+json`, `application/ld+json`, `text/turtle`).

## Capabilities

### New Capabilities
- `domain-migration-cloudflare-rules`: Migrate local deployment to iqoqo.kruk.cc and codify Cloudflare WAF/Bot rules for Semantic and Fediverse agents

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

Deployment environment configuration, Cloudflare SRE documentation and automation.

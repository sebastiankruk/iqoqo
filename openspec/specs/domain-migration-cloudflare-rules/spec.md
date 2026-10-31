# domain-migration-cloudflare-rules Specification

## Purpose
Migrate local deployment to iqoqo.kruk.cc and codify Cloudflare WAF/Bot rules for Semantic and Fediverse agents.

## Requirements

### Requirement: Cloudflare Semantic & ActivityPub Whitelist

The deployment rules SHALL permit Fediverse and Semantic Web crawlers to access public endpoints without interactive JavaScript challenges.

#### Scenario: ActivityPub request bypasses Cloudflare challenge

- **WHEN** A remote server requests /.well-known/webfinger or an actor profile with Accept: application/activity+json
- **THEN** Cloudflare passes the request through without presenting a bot challenge.

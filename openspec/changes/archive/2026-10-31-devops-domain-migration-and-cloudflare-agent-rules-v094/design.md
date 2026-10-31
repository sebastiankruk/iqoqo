## Context

Delivers 'Migrate local deployment of iqoqo.cc to iqoqo.kruk.cc' and 'Configure Cloudflare to let Agents read semantics'.

## Goals / Non-Goals

**Goals:**
- Zero federated communication drops caused by edge CDN bot blocks.

**Non-Goals:**
- Disabling DDoS protection or rate limiting.

## Decisions

### MIME-Based WAF Rules
* **Decision**: Match on `Accept` header containing activity+json or ld+json alongside path prefixes.
* **Rationale**: Granular bypass that protects standard browser routes.

## Risks / Trade-offs

- ('[Risk] Scrapers abusing semantic bypass', 'Mitigation: Enforce Flask-Limiter and Nginx rate limits behind Cloudflare.')

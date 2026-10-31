# Cloudflare Semantic & Fediverse WAF Rules

This document codifies the Cloudflare Custom Rules, WAF expressions, and Bot Management bypass policies required for iQoQo (`iqoqo.kruk.cc` and `iqoqo.cc`).

## Background & Rationale

iQoQo is a federated bibliographic catalog supporting ActivityPub (W3C), WebFinger (RFC 7033), NodeInfo (2.1), and Semantic Web / Linked Open Data (RDF, JSON-LD, Turtle).

When an instance is deployed behind Cloudflare:

1. Remote Fediverse instances (Mastodon, BookWyrm, Peer instances) deliver server-to-server HTTP POST and GET requests signed with HTTP Signatures (`draft-cavage-http-signatures-12`).
2. Linked Data consumers and Semantic Web crawlers fetch entity graphs via `Accept: application/ld+json` or `Accept: text/turtle`.
3. Cloudflare's default **Bot Fight Mode** or **Super Bot Fight Mode** flags non-browser automated user agents and serves interactive JavaScript challenges (Cloudflare Turnstile / Managed Challenge) or HTTP 403 Forbidden responses.
4. ActivityPub servers and semantic indexers do not execute JavaScript, causing silent federation failure, rejected friend requests, and broken WebFinger discovery.

To prevent communication drops while maintaining DDoS protection on user-facing web pages, Cloudflare Custom Rules must bypass bot challenges for semantic paths and MIME types.

---

## Cloudflare Custom Rules (Ruleset Engine)

### Rule 1: ActivityPub & Fediverse Protocol Whitelist

- **Rule Name**: `Allow ActivityPub and Fediverse S2S Traffic`
- **Phase**: `http_request_firewall_custom`
- **Action**: `Skip`
  - *Skip Components*:
    - All remaining custom rules (optional)
    - WAF Managed Rules
    - Bot Fight Mode / Super Bot Fight Mode (Bot Management)
    - Browser Integrity Check (BIC)

#### Expression (Wireshark / Ruleset Filter Syntax)

```text
(http.request.uri.path in {"/.well-known/webfinger" "/.well-known/nodeinfo" "/.well-known/host-meta"}) or
(starts_with(http.request.uri.path, "/api/federation/")) or
(starts_with(http.request.uri.path, "/federation/")) or
(any(http.request.headers["accept"][*] contains "application/activity+json")) or
(any(http.request.headers["accept"][*] contains "application/jrd+json"))
```

---

### Rule 2: Semantic Web & Linked Open Data (LOD) Whitelist

- **Rule Name**: `Allow Semantic Web Linked Data Crawlers`
- **Phase**: `http_request_firewall_custom`
- **Action**: `Skip`
  - *Skip Components*:
    - Bot Fight Mode / Super Bot Fight Mode
    - Browser Integrity Check

#### Expression (Wireshark / Ruleset Filter Syntax)

```text
(starts_with(http.request.uri.path, "/api/public/rdf/")) or
(any(http.request.headers["accept"][*] contains "application/ld+json")) or
(any(http.request.headers["accept"][*] contains "text/turtle")) or
(any(http.request.headers["accept"][*] contains "application/n-triples"))
```

---

## Defense in Depth Behind Cloudflare

Bypassing Cloudflare Bot Management on these specific paths does NOT leave the backend unprotected:

1. **Flask Rate Limiting**: All public federation endpoints (`/api/federation/inbox`, `/api/federation/outbox`, `/api/federation/directory`, `/.well-known/webfinger`) enforce strict rate limits via `Flask-Limiter` (`@limiter.limit("60 per minute")`).
2. **Payload Size Limits**: ActivityPub inboxes strictly reject payloads exceeding 100 KB (`MAX_ACTIVITY_SIZE = 100 * 1024`).
3. **HTTP Signature Verification**: All mutating S2S inbox requests must provide cryptographically verified RSA-SHA256 signatures with valid timestamps ($\pm 300\text{s}$) matching the sender's public key.
4. **Nginx Edge Limiting**: Local Nginx configuration in `deploy/nginx.conf` maintains independent connection and request rate limit zones (`zone=iqoqo_api`).

---

## Provisioning via Cloudflare API

To provision these rules programmatically via the Cloudflare v4 REST API:

```bash
curl -X POST "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/rulesets/phases/http_request_firewall_custom/entrypoint" \
     -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
     -H "Content-Type: application/json" \
     -d '{
       "rules": [
         {
           "action": "skip",
           "action_parameters": {
             "ruleset": "current",
             "phases": [
               "http_request_firewall_managed"
             ],
             "products": [
               "bic",
               "securityLevel"
             ]
           },
           "expression": "(http.request.uri.path in {\"/.well-known/webfinger\" \"/.well-known/nodeinfo\" \"/.well-known/host-meta\"}) or (starts_with(http.request.uri.path, \"/api/federation/\")) or (starts_with(http.request.uri.path, \"/federation/\")) or (any(http.request.headers[\"accept\"][*] contains \"application/activity+json\")) or (any(http.request.headers[\"accept\"][*] contains \"application/jrd+json\")) or (starts_with(http.request.uri.path, \"/api/public/rdf/\")) or (any(http.request.headers[\"accept\"][*] contains \"application/ld+json\")) or (any(http.request.headers[\"accept\"][*] contains \"text/turtle\"))",
           "description": "Bypass Bot Management and Managed Challenges for ActivityPub and Semantic Linked Data",
           "enabled": true
         }
       ]
     }'
```

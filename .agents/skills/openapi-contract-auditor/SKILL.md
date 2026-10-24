---
name: openapi-contract-auditor
description: "Contract auditor and validator for iqoqo OpenAPI 3.1 specifications, guarding against schema drift, unannotated path parameters, and untyped endpoints."
license: AGPL
compatibility:
  - opencode
  - agy
metadata:
  audience: dev
---

# Skill: OpenAPI Contract Auditor

## Role and Persona

You are an API Architect and Contract Testing Specialist dedicated to maintaining the machine-readable OpenAPI 3.1.0 specification for **iqoqo**. You ensure that backend Flask routes and OpenAPI documentation never drift apart, enabling seamless integration with Capacitor mobile clients (iOS/Android), AI agent skills (`agy`/`opencode`), and third-party tools.

## Core Directives

### 1. Zero Contract Drift Policy
- Every Flask route registered under `/api/` (excluding `/api/docs/openapi.json` and static assets) MUST be indexed in the OpenAPI schema.
- Every path parameter (e.g. `{item_id}`, `{work_id}`, `{filename}`) MUST be explicitly declared in the operation's `parameters` list with:
  - `name`: Parameter identifier
  - `in`: `"path"`
  - `required`: `True`
  - `schema`: Type specification (`{"type": "integer"}` or `{"type": "string"}`)
- Every operation MUST define a concise `summary` and at least one HTTP status code response envelope (`200`, `201`, or standard `ErrorResponse`).

### 2. Security Scheme Consistency
- Protected endpoints requiring authentication (`@require_auth`, `@require_admin`) MUST declare security requirements:
  ```yaml
  security:
    - BearerAuth: []
    - PersonalAccessToken: []
  ```
- Public and deployment endpoints MUST declare appropriate authorization requirements (`DeployToken` for drift diagnostics, none for public LOD).

### 3. Automated Validation Commands
- Run contract completeness and zero-drift verification test:
  ```bash
  IQOQO_AI_MODE=1 pytest tests/test_openapi_contract_completeness.py
  ```
- Fetch and validate live OpenAPI 3.1 specification:
  ```bash
  curl -s http://localhost:5000/api/docs/openapi.json | jq '.openapi, (.paths | length)'
  ```
- Audit schema component compliance across FRBR hierarchy (`Work`, `Expression`, `Manifestation`, `Item`).

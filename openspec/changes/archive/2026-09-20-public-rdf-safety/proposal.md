## Why

The public RDF surface currently accepts attacker-controlled collection limits, materializes full collections before “streaming,” exposes enrichment records without a visibility policy, and emits invalid concatenated JSON-LD chunks. This creates unauthenticated denial-of-service and privacy risks and undermines the release’s linked-data contract.

## What Changes

- Enforce safe upper bounds and validation for public RDF limits, pagination, and sitemap generation.
- Stream from bounded database iterators rather than converting the entire public collection to a list first.
- Make public RDF enrichment explicitly visibility-aware; exclude private collection names, image scans, and other non-public inventory metadata.
- Emit one valid JSON-LD document for streamed JSON-LD responses, or explicitly define a separate line-delimited media type.
- Consolidate content-negotiation behavior and add tests for combined response parsing, limits, privacy, and first-byte/bounded-memory behavior.

## Capabilities

### New Capabilities

### Modified Capabilities

- `semantic/rdf-serialization`: Require bounded, valid multi-format streaming and visibility-aware relational enrichment.
- `semantic/schema-org-seo`: Require public linked-data endpoints to expose only intentionally public records and valid negotiated representations.

## Impact

- `app/api/public.py`, `app/core/frbr_service.py`, public feed/sitemap behavior, and RDF tests.
- Potential response pagination/streaming contract clarification for clients requesting JSON-LD.
- No authentication changes; public endpoints remain public but safer.

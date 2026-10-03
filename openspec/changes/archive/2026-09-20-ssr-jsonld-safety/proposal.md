## Why

The 0.8.0 release embeds catalog and user-controlled values in raw SSR JSON-LD scripts using `dangerouslySetInnerHTML` with plain `JSON.stringify()`. A title, author, profile bio, or shared-collection description containing `</script>` can break out of the script and execute stored XSS; this must be fixed before shipping the semantic pages.

## What Changes

- Introduce one shared HTML-safe JSON-LD serialization boundary for every SSR structured-data payload.
- Escape script-breaking characters while preserving valid JSON-LD for crawlers and Schema.org consumers.
- Apply the boundary to Work, Expression, Manifestation, Item, public profile, shared collection, and collection-page structured data.
- Add regression tests using malicious catalog and user-controlled strings, including `</script>` and HTML entity cases.
- Preserve current JSON-LD vocabulary, page metadata, and client-rendered text behavior.

## Capabilities

### New Capabilities

### Modified Capabilities

- `semantic/schema-org-seo`: Require SSR JSON-LD to remain valid JSON-LD while treating all catalog and profile values as untrusted HTML-script input.

## Impact

- Frontend structured-data components and SSR routes under `frontend/app/`.
- Shared Schema.org builder/serialization utilities.
- Frontend Vitest coverage and production build output.
- No API or database schema changes.

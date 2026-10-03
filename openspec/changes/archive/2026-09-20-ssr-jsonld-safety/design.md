## Context

The release has several SSR pages and structured-data components that currently write `JSON.stringify()` output through `dangerouslySetInnerHTML`. The application already centralizes Schema.org object construction in `frontend/lib/schema-org.ts`, so the safest boundary is a single serializer/component shared by all callers.

## Goals / Non-Goals

**Goals:**

- Make every SSR JSON-LD sink safe for untrusted catalog and user text.
- Preserve JSON-LD parsing, Schema.org semantics, and existing page markup.
- Add a reusable test fixture for script-breaking payloads.

**Non-Goals:**

- Sanitizing ordinary React text nodes; React already escapes those.
- Changing the Schema.org vocabulary or page metadata contract.
- Treating JSON-LD as a substitute for server-side authorization.

## Decisions

1. **Escape at the final HTML-script boundary.** Build JSON-LD as typed objects as today, then serialize with a helper that escapes `<`, `>`, `&`, and script-sensitive Unicode separators. Escaping only at individual builders would miss future sinks.
2. **Use one shared component/helper.** Work, Expression, Manifestation, Item, public profile, shared collection, and collection layout callers must route through the same helper so future pages cannot silently reintroduce the raw sink.
3. **Keep JSON-LD semantics unchanged.** The escaped characters decode back to the original string when a JSON-LD parser reads the script.
4. **Test rendered source and parsed payload.** Tests must assert both that source cannot contain a literal closing script sequence from input and that the resulting JSON parses to the original value.

## Risks / Trade-offs

- [Risk] Search-engine fixtures may assert literal source strings → update fixtures to parse JSON-LD rather than compare unsafe source text.
- [Risk] A new page may bypass the helper → add a review/test search for raw JSON-LD sinks and document the helper as the only supported boundary.

## Migration Plan

Deploy the shared serializer with all current callers in one frontend release. Rollback is a frontend-only revert; no persisted data or API migrations are involved.

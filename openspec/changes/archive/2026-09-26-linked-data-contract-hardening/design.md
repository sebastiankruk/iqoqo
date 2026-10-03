## Context

The release currently mints different URL shapes in public RDF and authenticated export, uses multiple FRBR namespace styles, and validates only ontology class-name presence. Frontend `expressionKind` is accepted by the mapper but is not used.

## Goals / Non-Goals

**Goals:**

- Establish one canonical semantic identity and vocabulary contract.
- Make ontology drift checks useful as a release gate.
- Align backend RDF and frontend Schema.org event mappings.
- Validate enriched graphs, not only minimal happy-path graphs.

**Non-Goals:**

- Introducing federation protocols or external entity linking.
- Changing the underlying FRBR relational model.
- Removing compatibility aliases immediately; migration may require redirects/aliases.

## Decisions

1. **Canonical IRI source.** Use the configured canonical base URL plus one documented route policy; serializers must call shared IRI helpers rather than construct route-specific variants.
2. **Namespace ownership.** Select the documented FRBR namespace for each class/property and represent iqoqo-specific relationships with the iqoqo namespace. Update SHACL shapes and serializers together.
3. **Ontology gate by normalized triples.** Compare expected class/property/domain/range/shape declarations through a deterministic report; `make sync-ontology` invokes strict check mode by default.
4. **Event mapping is shared policy.** Define precedence for Expression kind, content type, and format once, then apply it in backend RDF and frontend JSON-LD builders.
5. **Cross-format contract tests.** Build one fixture with contributors, parts, image scans, collections, event metadata, and provenance; compare canonical IRIs and run SHACL validation on each representation.

## Risks / Trade-offs

- [Risk] Canonical IRI changes can break external bookmarks → preserve compatibility aliases/redirects and document the migration.
- [Risk] Existing graphs contain mixed namespaces → provide normalization/compatibility tests before tightening validation.
- [Risk] Ontology checks become expensive → cache parsed graphs and compare focused normalized declarations in CI.

## Migration Plan

First land report-only identity/ontology diagnostics. Fix serializers and tests, then enable strict CI failure. Keep legacy URL aliases until the next major semantic contract window.

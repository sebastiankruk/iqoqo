## 1. Public request and fetching policy

- [x] 1.1 Centralize RDF format negotiation and safe limit parsing with explicit maximums, and verify all public RDF routes share the policy.
- [x] 1.2 Replace full-list public profile/shared collection fetches with bounded iterators/pages, and verify first-chunk generation does not load the full collection.
- [x] 1.3 Preserve sitemap bounds, cache headers, expiry filtering, and rate limiting, and verify sitemap regression tests pass.

## 2. Visibility-aware serialization

- [x] 2.1 Define public-safe and authenticated-export enrichment profiles, and verify the profile is selected by endpoint context.
- [x] 2.2 Exclude private UserCollection and ImageScan data from public RDF, and verify private triples are absent in parsed graphs.
- [x] 2.3 Add tests for public item privacy, shared collection privacy, and authenticated export enrichment, and verify all pass.

## 3. Format validity

- [x] 3.1 Implement one valid JSON-LD streaming envelope or document the explicit NDJSON alternative, and verify the chosen media type is correct.
- [x] 3.2 Add tests that parse the complete HTTP body for JSON-LD, Turtle, and N-Triples, and verify no concatenated-document failures.
- [x] 3.3 Add bounded-memory/first-chunk integration coverage and run public API regression tests, recording successful results.

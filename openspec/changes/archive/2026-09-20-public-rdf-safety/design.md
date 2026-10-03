## Context

Public RDF routes currently fetch lists with caller-provided limits, then pass those lists to a chunk generator. The serializer also performs relational enrichment without knowing whether the caller is public, shared, or the authenticated owner.

## Goals / Non-Goals

**Goals:**

- Bound unauthenticated work and memory.
- Preserve valid Turtle, N-Triples, and JSON-LD representations.
- Separate public-safe enrichment from owner export enrichment.
- Keep profile/share/item URL contracts compatible for normal clients.

**Non-Goals:**

- Redesigning the public profile or share-token authorization model.
- Making every catalog entity private; catalog metadata remains public where current policy permits.
- Replacing sitemap generation with a separate indexing service.

## Decisions

1. **Use a shared public request policy.** Centralize limit parsing, maximums, and negotiation so all public RDF routes behave consistently.
2. **Use iterator-based fetching.** Fetch bounded pages/chunks from the database and pass iterators into the serializer; do not call `.all()` for the entire requested collection before streaming.
3. **Pass visibility context into enrichment.** Public serializers use an allowlisted enrichment profile; authenticated exports use a separate owner profile. Absence of an explicit public flag means omit inventory-linked data.
4. **Use one JSON-LD envelope.** Maintain an opening context/graph and closing envelope across chunks, or choose a clearly documented NDJSON media type. Do not concatenate independent JSON documents under `application/ld+json`.
5. **Retain bounded sitemap behavior.** Keep a hard URL limit, cache headers, and rate limiting; optimize later if the catalog requires sitemap indexes.

## Risks / Trade-offs

- [Risk] Some existing clients request very large limits → return a clear maximum and require pagination.
- [Risk] Public RDF loses enrichment that users expected → document the privacy boundary and keep richer owner export available.
- [Risk] Streaming envelope failures can produce malformed output after headers are sent → generate/validate chunk framing in tests before rollout.

## Migration Plan

Deploy server-side policy and serializer changes together. Existing requests under the new cap remain compatible; clients using larger limits must follow pagination. No database migration is required.

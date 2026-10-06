## Context

The v0.8.0 release passed final code review with all critical issues resolved. The review identified 7 LOW-severity observations and test coverage gaps that are non-blocking but should be addressed before v0.9.0. This change parks those items in v0.8.3 to prevent them from being forgotten while keeping the v0.8.0 release focused.

See proposal.md for the full list of items and motivation.

## Goals / Non-Goals

**Goals:**
- Add inline documentation for implicit relationship handling in ETL
- Add memory safety limit for Work loading in SPARQL graph construction
- Improve JSON-LD streaming fallback robustness
- Document format_type strict/non-strict validation tradeoff
- Add 3 new test suites (public RDF E2E, SPARQL chaos, ETL performance)
- Ensure all changes are backward-compatible and non-breaking

**Non-Goals:**
- Refactoring existing SPARQL/RDF/ETL architecture
- Changing API contracts or response formats
- Implementing strict format_type validation by default (deferred to v0.9.0 after taxonomy stabilization)
- Performance optimization beyond the specific memory safety concern

## Decisions

### Decision 1: Configurable Work limit vs hard-coded limit

**Choice:** Add `MAX_GRAPH_WORKS` as a configurable constant (default 10,000) similar to existing `MAX_GRAPH_ITEMS`

**Rationale:** 
- Works are typically far fewer than Items, but large catalogs could have 100K+ Works
- Hard-coded limit would be too rigid for different deployment sizes
- Configurable limit allows operators to tune based on available memory
- Consistent with existing pattern (MAX_GRAPH_ITEMS, MAX_GRAPH_TRIPLES)

**Alternatives considered:**
- Hard-coded limit of 50,000 — too rigid
- Dynamic limit based on available memory — too complex for v0.8.3
- No limit (status quo) — risks memory exhaustion on very large catalogs

### Decision 2: JSON-LD streaming fallback strategy

**Choice:** Log warning and skip unparseable chunks rather than producing malformed JSON

**Rationale:**
- Current fallback (yield raw chunk) could produce invalid JSON mid-stream
- Skipping with warning is safer and allows consumers to detect partial results
- Alternative (crashing entire response) is worse — loses all data
- Consumers should handle partial results gracefully anyway

**Alternatives considered:**
- Crash on unparseable chunk — loses entire response
- Yield raw chunk (current) — produces invalid JSON
- Buffer and retry — too complex, adds latency

### Decision 3: format_type strict mode default

**Choice:** Keep non-strict mode as default, add documentation explaining tradeoff

**Rationale:**
- Strict mode would break existing catalogs with non-taxonomy format_type values
- Forward compatibility is important for new format types
- Taxonomy pollution is a concern but not critical for v0.8.3
- Can switch to strict default in v0.9.0 after taxonomy stabilization

**Alternatives considered:**
- Switch to strict mode by default — breaking change
- Remove non-strict mode entirely — too restrictive
- Add validation warning in logs — good, but not sufficient documentation

### Decision 4: Test scope and location

**Choice:** Add 3 new test files in existing test directories

**Rationale:**
- Public RDF E2E test: `tests/test_public_rdf_streaming_e2e.py` — verifies multi-chunk validity
- SPARQL chaos test: `tests/test_sparql_chaos.py` — stress tests under memory pressure
- ETL performance test: `tests/test_etl_frbr_performance.py` — validates 10K+ row handling
- Keeps tests close to related code, follows existing patterns

**Alternatives considered:**
- Add tests to existing files — would make them too large
- Create new test directory — unnecessary structure change
- Skip performance tests — would leave gap in coverage

## Risks / Trade-offs

**Risk:** Configurable Work limit adds complexity
→ **Mitigation:** Single constant, well-documented, follows existing pattern

**Risk:** JSON-LD fallback change could affect existing consumers
→ **Mitigation:** Fallback path is rare, consumers should handle partial results anyway, logged warnings help debugging

**Risk:** Performance tests may be flaky on CI
→ **Mitigation:** Use generous timeouts, focus on correctness not speed, skip on resource-constrained CI

**Risk:** format_type documentation may not be read
→ **Mitigation:** Add docstring, inline comments, and link from migration guide

**Trade-off:** Non-strict format_type mode allows taxonomy pollution
→ **Acceptable for v0.8.3:** Forward compatibility > strict validation at this stage. Can enforce strict mode in v0.9.0 after taxonomy stabilizes.

## Migration Plan

No migration required — all changes are additive or documentation-only.

**Deployment steps:**
1. Deploy code changes (backward-compatible)
2. Run existing test suite to verify no regressions
3. Run new test suites to verify new functionality
4. Monitor SPARQL memory usage on production (should decrease for large catalogs)

**Rollback strategy:**
- All changes are backward-compatible
- Can revert individual commits if issues arise
- No database schema changes

## Open Questions

_None — all decisions resolved in this design document._

## Why

The v0.8.0 release passed final code review with all critical issues resolved, but the review identified 7 LOW-severity observations and test coverage gaps that should be addressed before v0.9.0. These items are non-blocking for the v0.8.0 release but represent opportunities to improve code clarity, robustness, and test coverage. Parking them in v0.8.3 prevents them from being forgotten while keeping the v0.8.0 release focused on its critical deliverables.

## What Changes

- **ETL documentation**: Add inline comment in `apply_manifestation_merge_plan()` explaining that `ItemTag` and `ItemStatusLog` are handled implicitly via Item reparenting (they reference `item_id`, not `manifestation_id`)
- **SPARQL memory safety**: Add configurable limit for Work loading in `build_graph()` to prevent memory exhaustion on catalogs with 100K+ Works
- **JSON-LD streaming robustness**: Improve fallback handling in `frbr_service.py:2158-2163` to ensure malformed chunks don't produce invalid JSON mid-stream (currently acceptable but could be more defensive)
- **F3 format_type validation**: Document the strict/non-strict mode tradeoff in `f3_validation.py:255` and consider defaulting to strict mode for new manifestations to prevent taxonomy pollution
- **Public RDF E2E test**: Add end-to-end test for public RDF streaming with >1 chunk to verify the `@graph` container produces valid JSON-LD across chunk boundaries
- **SPARQL chaos test**: Add stress test for SPARQL child process under memory pressure (OOM scenario) to verify resource limits prevent system-wide impact
- **ETL performance test**: Add test with >10K rows to verify the safe ETL script performs acceptably on production-scale data

## Capabilities

### New Capabilities

_None — this is a maintenance sweep, not a feature addition._

### Modified Capabilities

- `semantic/sparql-release-hardening`: Add memory-bounded Work loading requirement and chaos test coverage
- `semantic/rdf-serialization`: Add JSON-LD streaming fallback robustness requirement and multi-chunk E2E test
- `scripts/etl-frbr-safe`: Add inline documentation for implicit relationship handling and performance test coverage
- `semantic/f3-column-promotion`: Add format_type strict mode documentation and validation policy clarification

## Impact

- **Code**: Minor additions to 4 files (sparql_service.py, frbr_service.py, etl_frbr_safe.py, f3_validation.py) — no breaking changes
- **Tests**: 3 new test files or test additions (public RDF E2E, SPARQL chaos, ETL performance)
- **Documentation**: Inline comments and docstring updates
- **APIs**: No API changes
- **Dependencies**: No new dependencies
- **Performance**: Potential memory improvement for very large catalogs (SPARQL Work loading limit)
- **Risk**: Very low — all changes are defensive improvements or test additions

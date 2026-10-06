## 1. SPARQL Memory Safety

- [ ] 1.1 Add `MAX_GRAPH_WORKS = 10000` constant to `app/core/sparql_service.py` with docstring explaining the limit, and verify the constant is defined and documented
- [ ] 1.2 Modify `build_graph()` in `app/core/sparql_service.py` to apply `MAX_GRAPH_WORKS` limit when loading Works, log a warning when the limit is reached, and verify the limit is enforced by running a test with >10K Works
- [ ] 1.3 Add unit test in `tests/test_sparql_hardening.py` to verify Work limit enforcement, and verify the test passes with both under-limit and over-limit scenarios

## 2. JSON-LD Streaming Robustness

- [ ] 2.1 Review JSON-LD streaming fallback in `app/core/frbr_service.py:2158-2163` and determine if the current fallback produces malformed JSON, and verify the behavior with a test case
- [ ] 2.2 Modify the fallback handler to skip unparseable chunks with a logged warning instead of yielding raw content, and verify the modified code produces valid JSON-LD even when chunks fail
- [ ] 2.3 Add unit test in `tests/test_rdf_serialization.py` to verify JSON-LD streaming produces valid output when a chunk fails to parse, and verify the test passes

## 3. F3 format_type Validation Documentation

- [ ] 3.1 Add docstring to `validate_format_type()` in `app/core/f3_validation.py` explaining the strict/non-strict mode tradeoff, forward compatibility rationale, and taxonomy pollution risk, and verify the docstring is present and clear
- [ ] 3.2 Add inline comment in `validate_format_type()` explaining why non-strict mode accepts unknown formats and when to switch to strict mode, and verify the comment is present
- [ ] 3.3 Update module-level docstring in `app/core/f3_validation.py` to document the validation policy and recommend strict mode for new deployments, and verify the documentation is comprehensive

## 4. ETL Implicit Relationship Documentation

- [ ] 4.1 Add inline comment in `apply_manifestation_merge_plan()` in `scripts/etl_frbr_safe.py` explaining that ItemTag and ItemStatusLog are handled implicitly via Item reparenting (they reference item_id, not manifestation_id), and verify the comment is present and clear
- [ ] 4.2 Add inline comment in the relationship inventory section of `scripts/etl_frbr_safe.py` clarifying which relationships are explicitly reparented vs implicitly handled, and verify the comments are accurate

## 5. Public RDF Multi-Chunk E2E Test

- [ ] 5.1 Create `tests/test_public_rdf_streaming_e2e.py` with test infrastructure for multi-chunk streaming, and verify the file is created and imports correctly
- [ ] 5.2 Add test case to verify JSON-LD streaming with >1 chunk produces valid concatenated output, and verify the test passes with a collection large enough to span multiple chunks
- [ ] 5.3 Add test case to verify Turtle streaming with >1 chunk produces valid concatenated output, and verify the test passes
- [ ] 5.4 Add test case to verify N-Triples streaming with >1 chunk produces valid concatenated output, and verify the test passes

## 6. SPARQL Chaos Test

- [ ] 6.1 Create `tests/test_sparql_chaos.py` with test infrastructure for stress testing, and verify the file is created and imports correctly
- [ ] 6.2 Add test case to verify SPARQL child process behavior under memory pressure (approaching MAX_GRAPH_TRIPLES limit), and verify the test passes and the child is terminated gracefully
- [ ] 6.3 Add test case to verify repeated timeout floods (multiple concurrent queries all timing out) don't leave zombie processes or exhaust resources, and verify the test passes
- [ ] 6.4 Add test case to verify the system remains available after a chaos test completes, and verify subsequent queries succeed

## 7. ETL Performance Test

- [ ] 7.1 Create `tests/test_etl_frbr_performance.py` with test infrastructure for large-scale ETL testing, and verify the file is created and imports correctly
- [ ] 7.2 Add test case to verify ETL reconciliation completes within acceptable time bounds for 10K+ manifestations, and verify the test passes with a generated dataset
- [ ] 7.3 Add test case to verify ETL memory usage remains bounded during large-scale reconciliation, and verify the test passes without excessive memory growth

## 8. Integration Verification

- [ ] 8.1 Run full test suite (`pytest tests/`) and verify all existing tests still pass with no regressions
- [ ] 8.2 Run new test suites and verify all new tests pass
- [ ] 8.3 Run linting (`ruff check`, `black --check`, `isort --check`) and verify all code passes style checks
- [ ] 8.4 Verify SPARQL endpoint still works correctly with a manual test query against a test database
- [ ] 8.5 Verify public RDF endpoint still produces valid output with a manual test request

## 9. Documentation and Release Notes

- [ ] 9.1 Update CHANGELOG.md with v0.8.3 entry listing all minor improvements and test additions, and verify the changelog is accurate
- [ ] 9.2 Update any relevant API documentation if behavior changed (should be minimal), and verify documentation is accurate
- [ ] 9.3 Create pull request with all changes and verify PR description references this OpenSpec change

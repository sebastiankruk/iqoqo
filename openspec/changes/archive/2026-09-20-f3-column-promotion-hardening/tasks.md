## 1. Migration preflight and rollback

- [x] 1.1 Add preflight checks for publisher lengths, duplicate/invalid ISBNs, mixed-case promoted keys, and migration conflicts, and verify production-like fixtures are reported.
- [x] 1.2 Change migration ordering so incompatible data is handled before narrowing columns or enforcing uniqueness, and verify upgrade succeeds only after preflight passes.
- [x] 1.3 Define and test reversible metadata behavior or enforce the required verified backup contract, and verify rollback behavior.

## 2. Runtime validation

- [x] 2.1 Add shared case-insensitive promoted-key extraction with deterministic column-vs-metadata precedence, and verify mixed-case fixtures.
- [x] 2.2 Normalize valid ISBN-10/hyphenated ISBNs and reject invalid ISBN-13 length/checksum values, and verify API/service error contracts.
- [x] 2.3 Normalize and validate `publisher` and `format_type` against length and taxonomy rules, and verify accepted/rejected values.

## 3. Verification

- [x] 3.1 Add SQLite and PostgreSQL migration tests for long publishers, conflicts, upgrade, downgrade, and row preservation, and verify both dialects.
- [x] 3.2 Add service/API tests for ISBN, mixed-case metadata, malformed values, and format taxonomy handling, and verify all pass.
- [x] 3.3 Run FRBR integrity and full backend regression suites, and record migration release-gate results.

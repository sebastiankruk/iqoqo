## Context

The current migration narrows `publisher` before fully handling long values and prunes promoted metadata keys. Runtime creation/update paths normalize formatting but do not consistently canonicalize ISBNs or validate checksums/casing variants.

## Goals / Non-Goals

**Goals:**

- Make upgrades safe on real v0.7.x data.
- Establish one canonical extraction/validation policy shared by migration and runtime writes.
- Provide deterministic rollback/preflight diagnostics.

**Non-Goals:**

- Adding arbitrary new media taxonomies in this change.
- Reworking all metadata normalization outside promoted F3 attributes.

## Decisions

1. **Preflight before DDL.** Scan and report incompatible publisher lengths and identifier conflicts before narrowing columns or adding uniqueness constraints.
2. **Centralize legacy-key normalization.** Normalize keys case-insensitively through a shared adapter, retain unknown metadata, and make precedence explicit when both column and metadata values exist.
3. **Use a canonical ISBN validator.** Accept valid formatted ISBN-10/ISBN-13 inputs, convert where necessary, and reject malformed values instead of storing them in `isbn13`.
4. **Make rollback honest.** Either preserve enough metadata to reconstruct promoted values or require a verified backup and document the migration as operationally irreversible.
5. **Validate format taxonomy at the boundary.** Use the shared taxonomy registry with a controlled extension path rather than an unbounded enum that blocks future media types.

## Risks / Trade-offs

- [Risk] Strict validation rejects legacy junk that was previously accepted → provide an audit/remediation command and clear error categories.
- [Risk] Truncating publisher data loses information → default to preflight rejection unless an operator explicitly chooses truncation.
- [Risk] ISBN uniqueness conflicts block migration → report conflicts and require manual reconciliation before DDL.

## Migration Plan

Run preflight against a production backup, remediate or approve all reported records, execute upgrade, validate row counts/values, and only then enable runtime strict validation. Rollback uses the documented backup path when metadata pruning has occurred.

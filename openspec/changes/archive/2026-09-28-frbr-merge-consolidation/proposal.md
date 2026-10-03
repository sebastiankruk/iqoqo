## Why

iqoqo currently has **two independent implementations of the same irreversible
operation**, and they disagree about what "merge" means. This was found while
auditing every foreign key that references `works.id`, `expressions.id`, and
`manifestations.id` against the code paths that re-point them.

### 1. The manual merge path silently destroys user data (P0)

`frbr_service.merge_frbr_entities()` (shipped in v0.8.1, reachable from the FRBR
editor's *Relation Management → Merge* tab) re-points only the direct child
entity and its contributions. It ignores every other table that references the
tier. Of the 13 columns that reference `works.id`, it covers 2.

| Tier | Referencing columns | Covered by `merge_frbr_entities` |
| ---- | ------------------- | ---------------------------------- |
| Work (F1) | 13 | 2 |
| Expression (F2) | 7 | 2 |
| Manifestation (F3) | 9 | 2 |

The uncovered columns are not inert. Eleven of them are `ON DELETE CASCADE`, so
deleting the source row silently deletes the dependent rows — including a user's
**wishlist entries** (`UserWorkIntent.work_id`), **box-set membership**
(`WorkPart`), **work expansions** (`WorkExpansionLink`), **container
aggregations** (`ContainerAggregation`), **social feedback** (`SocialFeedback`),
and **escalation requests** (`EscalationRequest`). The remainder are
`ON DELETE SET NULL`, which orphans rather than destroys.

**Verified on PostgreSQL 18** (the dedicated E2E instance), seeding one row of
every referencing kind against a single source Work and merging:

| Referencing row | After `merge_frbr_entities` | After `merge_work` (C15) |
| --------------- | --------------------------- | ------------------------ |
| `UserWorkIntent` (wishlist) | **0 — destroyed** | 1 |
| `WorkPart` (box set) | **0 — destroyed** | 1 |
| `WorkExpansionLink` | **0 — destroyed** | 1 |
| `ContainerAggregation` | **0 — destroyed** | 1 |
| `SocialFeedback` | **0 — destroyed** | 1 |
| `SocialNote` | **0 — destroyed** | 1 |
| `EscalationRequest` | **0 — destroyed** | 1 |
| `Expression` (child) | 1 | 1 |
| `WorkContribution` | **0 — destroyed** | 1 |

**8 of 9 referencing rows destroyed.** The C15 dedupe path preserves all nine.

### 1a. The manual merge also drops contributor attribution (P0)

A narrower probe on PostgreSQL separated three contribution shapes, because the
aggregate count above conflates them. `Work.contributions` is
`lazy="selectin", cascade="all, delete-orphan"`, and `merge_frbr_entities` ends
with `db.session.delete(source)`. Setting `work_id` directly on the child does
not update the parent's loaded collection, so the delete-orphan cascade still
sees the row as belonging to the source and deletes it.

| Contribution | Expected | `merge_frbr_entities` | `merge_work` (C15) |
| ------------ | -------- | --------------------- | ------------------ |
| source-only (`author`, seq 1) | follow the survivor | **deleted** | re-pointed |
| target-only (`translator`) | untouched | untouched | untouched |
| duplicate natural key | collapse to one | collapsed | collapsed |

Result on the survivor: 2 rows instead of 3 — a co-author vanishes from the
merged Work. `duplicate_service` avoids this only because its `_delete_source_row()`
issues a **Core-level** `DELETE`, which bypasses the ORM cascade entirely. That
was incidental, not designed, and is worth stating explicitly in the shared core.

This operation has **zero test coverage**. It is irreversible, and the archived
`editor/relation-management` spec already promises behavior it does not deliver
("all child entities of the source entity SHALL be reparented", "identifiers
(ISBN-13, UPC, EAN) are reconciled").

### 2. The safer implementation cannot merge Expressions (P1)

`duplicate_service.merge_work` / `merge_manifestation` re-point **every**
referencing column (13/13 and 9/9) and additionally reconcile ISBNs — but
`DuplicateCandidate.entity_tier` is constrained to `work` and `manifestation`.
Expressions cannot be merged through the review queue at all.

The result is an inverted capability split: the *lossy* implementation is the
only one that can reach F2, while the *audited* implementation cannot.

### 3. The LLM is doing less work than the design implies (P2)

Measurement of the two-stage detector shows the language model is almost
exclusively a **false-positive filter for same-author pairs**, not a semantic
matcher:

| A | B | Heuristic score | Reaches LLM? |
| - | - | --------------- | ------------ |
| The Lord of the Rings | …: The Two Towers | 0.75 | yes — *shared creator only* |
| Dune | Dune: Messiah | 0.75 | yes — *shared creator only* |
| Neuromancer | Snow Crash | 0.75 | yes — *shared creator only* |

The hard cases the LLM was introduced for are already rejected by the `0.72`
title-similarity floor (LOTR vs Two Towers scores `0.69`, Hobbit vs An
Unexpected Journey `0.35`) and never reach it. The one line that floods the
queue is the creator-overlap escape hatch, which grants `0.75` **regardless of
title similarity**.

Meanwhile pairs a language model would genuinely excel at — cross-language
equivalents such as *Der Fremde* / *The Stranger* — share no blocking key, so
they are never compared at all. The blocking stage removes the cases that need
semantics before the LLM can see them.

A conclusive pair is also paying for an LLM call: an identical ISBN/EAN/UPC/
barcode returns a heuristic score of `1.0` ("full stop") and is then submitted
for evaluation anyway.

## What Changes

### Track 1 — Merge integrity (P0/P1, release gate)

- **BREAKING (bug fix):** Stop `merge_frbr_entities` from cascading away user
  data. Extract the reference-repointing logic from `duplicate_service` into one
  shared, table-driven core and route both entry points through it.
- **Add** `merge_expression` so the F2 tier is mergeable, and widen
  `DuplicateCandidate.entity_tier` to include `expression` (schema constraint,
  migration, API validation, and the review UI's tier discriminator).
- **Add** ISBN reconciliation to the manual merge path so a hand-initiated
  Manifestation merge preserves a conflicting ISBN instead of dropping it.
- **Add** a column-level coverage test that fails when any table referencing a
  merged tier is not in the re-point map, so a future column cannot be added
  silently un-covered.
- **Add** the missing test coverage for `merge_frbr_entities` across all three
  tiers, including the regression cases for every currently-missed column.
- Keep the public signatures of `frbr_service.merge_frbr_entities` and
  `duplicate_service.merge_work` / `merge_manifestation` unchanged so the
  existing `RelationManagementDialog` and the review UI keep working.

### Track 2 — Detection without mandatory inference (P2)

- **Add** deterministic classification ahead of inference: auto-accept a pair
  sharing a conclusive identifier (`isbn13` / `ean` / `upc` / `barcode`) and
  auto-reject a pair that shares a creator while failing the title floor.
- **Add** an `--engine heuristic|llama` selector to `scripts/detect_duplicates.py`
  and an `engine` field on the scan endpoint, defaulting to `heuristic` so a
  scan no longer requires a running Ollama instance.
- **Retain** the LLM path unchanged, including the rationale string surfaced to
  the reviewer, so `llama` remains available where it earns its cost.

## Capabilities

### New Capabilities

- `frbr/merge-integrity`: one audited merge core covering every referencing
  table for all three abstract FRBR tiers, safe re-parenting under
  `ON DELETE CASCADE`, identifier reconciliation, and merge-path parity between
  the manual and review-queue entry points.

### Modified Capabilities

- `operations/duplicate-detection`: the LLM becomes an optional refinement tier
  behind a deterministic classifier, and the candidate model gains the
  `expression` tier. *(This delta depends on `duplicate-detection-service` being
  archived first, so its `operations/duplicate-detection` capability exists in
  the main specs.)*

## Impact

- **Backend services:** `app/core/frbr_service.py`,
  `app/core/duplicate_service.py` — `merge_frbr_entities` delegates to the shared
  core; new `merge_expression`; a single tier → column map.
- **Database & models:** `DuplicateCandidate.entity_tier` check constraint gains
  `expression`, requiring an Alembic migration (`v0_8_2_…_expression_tier`) that
  relaxes the constraint in place and is reversible.
- **API & routing:** `POST /v1/admin/duplicates/scan` accepts an `engine` field;
  `GET /v1/admin/duplicates` may now return `expression`-tier candidates. The
  `POST /v1/admin/frbr/relations/merge` response shape is unchanged.
- **CLI:** `scripts/detect_duplicates.py` gains `--engine`.
- **Frontend:** the `DuplicateSide` discriminated union gains an Expression
  member; the review component renders an Expression comparison; the scan button
  selects the engine.
- **Dependencies:** none added. The default `heuristic` engine removes the
  Ollama runtime requirement from the detection path, which matters for
  containerized deployments without a GPU.
- **Risk:** Track 1 changes the behavior of an operation that is already
  irreversible, and its `reassign`/`split` siblings share `_ENTITY_CHILD_MAP`.
  The gate is the column-coverage test, not a code review.

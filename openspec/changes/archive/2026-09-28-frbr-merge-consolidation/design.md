# Design — FRBR Merge Consolidation

## Context

Two implementations of an irreversible operation exist, and they disagree.

| | `frbr_service.merge_frbr_entities` | `duplicate_service.merge_work` / `_manifestation` |
| --- | --- | --- |
| Shipped | v0.8.1 (C11) | unreleased (C15) |
| Entry point | FRBR editor *Relation Management → Merge* tab, `POST /frbr/relations/merge` | review queue, `POST /duplicates/<id>/merge` |
| Tiers | Work, Expression, Manifestation | Work, Manifestation |
| Referencing rows surviving a Work merge (PostgreSQL) | **1 of 9** | 9 of 9 |
| Source's unique contributor migrated | **no — deleted by cascade** | yes |
| ISBN reconciliation | no | yes (primary wins / adopt / `alternate_isbn13`) |
| Source row removal | `db.session.delete()` → ORM cascade | Core-level `delete()` → no cascade |
| Rollback wrapper | **none** — bare `db.session.commit()` | `except Exception: db.session.rollback(); raise` |
| Audit `change_type` | `"merge"` | `"merge_work"` / `"merge_manifestation"` |
| Rate limited | **no** | scan: `5 per minute` |
| Tests | **none** | 72 cases |

The capability split is inverted: the audited implementation cannot reach F2, and
the only implementation that can reach F2 is the lossy one.

The "source row removal" row is the subtle one. `Work.contributions` is
`lazy="selectin", cascade="all, delete-orphan"`. Re-pointing a child by assigning
its foreign-key column does **not** update the parent's already-loaded
collection, so an ORM `session.delete(source)` still sees the child in that
collection and cascades a delete to it. `duplicate_service` avoids this only
because `_delete_source_row()` issues a Core-level `DELETE` that bypasses ORM
cascade processing entirely. That is currently an accident of implementation, so
the shared core must make it an explicit invariant (D2) with a regression test
for the source-only-contribution shape.

## Goals

1. No merge path may destroy a row that references the merged entity.
2. One implementation, one audit vocabulary, one transaction contract.
3. A new referencing column cannot be added without being covered.
4. Detection no longer requires inference for its common path.

## Non-goals

- Not reworking `reassign_frbr_parent` or `split_frbr_entity` beyond the shared
  helpers they also need. They currently share `_ENTITY_CHILD_MAP`; the refactor
  keeps that map intact.
- Not adding a merge UI for Expressions as a separate page. Per the UX audit,
  the review queue is reused (see *Decisions* below).
- Not deprecating the Relation Management dialog. It remains the manual
  "I found a duplicate while browsing" entry point; it just becomes safe.

## Decisions

### D1 — A single tier → column map is the source of truth

Introduce a declarative map, one entry per abstract tier, listing every table
that references it and how to re-point it:

```python
@dataclass(frozen=True)
class _RefPoint:
    model: type
    fk_attribute: str
    unique_attributes: tuple[str, ...]   # empty => plain re-point
    polymorphic: bool = False             # SemanticLink, keyed by (entity_type, entity_id)
```

```python
_WORK_REFPOINTS: tuple[_RefPoint, ...] = (
    _RefPoint(Expression, "work_id", ()),
    _RefPoint(WorkContribution, "work_id", ("contributor_id", "role")),
    _RefPoint(WorkPart, "container_work_id", ("part_work_id",)),
    _RefPoint(WorkPart, "part_work_id", ("container_work_id",)),
    _RefPoint(WorkExpansionLink, "base_work_id", ("expansion_work_id",)),
    _RefPoint(WorkExpansionLink, "expansion_work_id", ("base_work_id",)),
    _RefPoint(ContainerAggregation, "container_work_id", (...)),
    _RefPoint(ContainerAggregation, "aggregated_work_id", ("container_work_id", "component_name")),
    _RefPoint(UserWorkIntent, "work_id", ("user_id", "expression_id", "manifestation_id")),
    _RefPoint(SocialFeedback, "work_id", ()),
    _RefPoint(SocialNote, "work_id", ()),
    _RefPoint(RoadmapItem, "work_id", ()),
    _RefPoint(EscalationRequest, "work_id", ()),
    _RefPoint(SemanticLink, "entity_id", (), polymorphic=True),
)
```

`Expression` and `Manifestation` get their own entries. `merge_work`,
`merge_manifestation`, and the new `merge_expression` all iterate their tier's
tuple; the manual endpoint resolves its tier to the same tuple.

*Why a map and not introspection.* Reflecting `__table__` metadata at runtime
would be clever but would also pick up columns that must **not** be re-pointed —
chiefly `resolved_by_id`-style actor columns and the unique-pair self-reference
on `DuplicateCandidate`. An explicit, reviewable list is the safety property we
are buying.

*Existing helpers are reused unchanged.* `_repoint_simple`, `_repoint_unique_child`,
`_repoint_semantic_links`, and `_delete_source_row` already implement the
strategies. They move to the shared module; the map only decides *what* to
re-point, not *how*.

### D2 — The source row is removed with a Core-level DELETE, always

**Invariant:** the shared core never calls `db.session.delete()` on the source
entity. It always removes the row with a Core-level `DELETE`.

*Why, from the PostgreSQL probe.* `Work.contributions` is
`lazy="selectin", cascade="all, delete-orphan"`. Re-pointing a contribution by
assigning `work_id` on the loaded child does **not** remove it from the parent's
already-loaded collection, so the ORM still considers it an orphan of the source
and deletes it. Measured on a source/target pair seeded with one source-only
contributor, one target-only contributor, and one duplicated natural key:

| | expected on survivor | `merge_frbr_entities` | `merge_work` |
| --- | --- | --- | --- |
| rows on the survivor | 3 | **2** | 3 |

A co-author silently disappears from the merged Work. `duplicate_service`
currently escapes this only because its `_delete_source_row()` issues a Core
`DELETE`, bypassing ORM cascade processing. That is an accident of
implementation rather than a design decision, so it becomes an explicit
invariant of the shared core, with a regression test that distinguishes
source-only, target-only, and duplicated contribution shapes — the aggregate
row count alone cannot tell them apart.

Note that `Work.expressions` and `Manifestation.items` do **not** exhibit this
(their backrefs are `lazy=True` lists rather than `selectin` collections), which
is why the original probes passed and this only surfaced under a targeted
PostgreSQL test.

### D3 — Completeness is enforced by a test, not by review

A test reflects the SQLAlchemy metadata for every foreign key targeting
`works.id`, `expressions.id`, and `manifestations.id`, and asserts each
`(model, column)` appears in the corresponding tier's map — except for an
explicit, individually-commented allowlist of columns that must not move.

*Why this is the release gate.* The P0 in this change was invisible to code
review, invisible to the existing 72 tests, and invisible to the archived spec.
Only a mechanical cross-check of the schema against the map catches it, and it
keeps catching it as columns are added. The allowlist is the escape hatch and is
forced to carry a justification.

The test runs with `PRAGMA foreign_keys=ON` on SQLite so `ON DELETE CASCADE`
behaves as it does on PostgreSQL, plus at least one behavioral case per tier.

### D4 — One transaction contract and one audit vocabulary

`merge_frbr_entities` gains the same `try/except Exception: rollback; raise`
wrapper and the same row locks (`SELECT … FOR UPDATE` on both entities, ordered
by id) that the dedupe path uses. Its `change_type` moves from the generic
`"merge"` to `merge_work` / `merge_expression` / `merge_manifestation`, matching
the dedupe path, so a single query reconstructs every merge regardless of origin.

The public signature `merge_frbr_entities(entity_type, source_id, target_id, user_id)`
and the endpoint's `{"success": true, "data": {"id": …}}` response are unchanged,
so `RelationManagementDialog` needs no change.

### D5 — Expression merges are blocked across realization boundaries

*Ontology constraint (from the ontologist review).* An Expression (F2) is a
specific intellectual/artistic realization — a language, a content type. Merging
the Polish audiobook of *The Hobbit* with its English print edition would
destroy the F2 distinction the whole hierarchy exists to express, and would
silently re-parent a user's `UserWorkIntent.expression_id` that deliberately
targeted one translation.

So a merge of two Expressions MUST be refused when `language` or `content_type`
differs, mirroring the existing F3 rule that different editions are not
duplicates. Refusal is a `DuplicateServiceError` / 400, not a silent
normalization.

*Detection-side consequence, and it is significant.* Screening for the
Manifestation tier already blocks on the **inherited parent Work title**, so
sibling Manifestations of one Work always collide. Expressions would inherit
that behaviour and be worse: **every Expression of a Work shares the Work's
title**, so an Expression scan would queue the entire catalog against itself.

Therefore Expression blocking keys must be built from the Expression's own
identity — `normalize_title(expression.label)`, plus the `(language,
content_type)` pair — and **must not** fall back to the parent Work title. A pair
whose `language` or `content_type` differs is rejected before scoring, never
queued. Only genuine near-duplicate realizations of the *same* Work reach the
queue.

### D6 — Deterministic classification precedes inference

Replace the pass-everything-to-the-LLM flow with a three-way classification.

```
screened pair
  ├─ conclusive identifier match (isbn13/ean/upc/barcode)  → AUTO_ACCEPT
  ├─ creator overlap AND title below floor                  → AUTO_REJECT
  └─ grey zone                                              → LLM (only in `llama` engine)
```

*Rationale (measured).* The creator-overlap rule at
`duplicate_service.py:752` grants `0.75` regardless of title similarity, so
`Neuromancer` vs `Snow Crash` and `Dune` vs `Dune: Messiah` are the bulk of the
queue. Those are answerable deterministically: same creator plus a title that
fails the similarity floor is a different work. Meanwhile an identical ISBN
already scores `1.0` in `_score_pair` yet is still submitted for inference.

*Consequence for the queue.* Candidates created by the `heuristic` engine have no
LLM `confidence` and no `reasoning`. `confidence` becomes nullable and a new
`resolution_source` column (`heuristic` | `llm`) records provenance.

*Default is `heuristic`.* A scan no longer requires a running Ollama, which
removes a hard runtime dependency from container deployments without a GPU. The
`llama` engine is retained verbatim, including the rationale string, because it
is genuinely useful to a human deciding.

### D7 — A scan score is not a merge decision

*UX review.* The review UI's confidence badge currently implies a calibrated
probability. Under the `heuristic` engine that is false: a `1.00` means
"identical ISBN", not "certainly the same". Presenting both identically is
misleading, so the badge MUST be labelled by provenance — `LLM 0.92` vs
`heuristic 1.00 (identical ISBN)` — and the rationale line MUST fall back to the
heuristic reasons when there is no LLM explanation.

The empty-state copy ("Run a scan to compare the catalog…") is also stale under
the default engine, where a scan is fast and needs no inference. It should
describe the outcome, not the prerequisite.

*Button density.* The candidate card already carries Dismiss plus a per-side
"Keep this one" toggle plus the merge action. Adding a third tier must not add
controls. The Expression tier reuses the identical card with an expression
comparison body, so per-card control count is unchanged at the current 4.
The `canEdit` gate continues to hide the whole mutation set for read-only
viewers, so the read-only card shows one control, not four.

### D8 — Manual merge gets the same rate limit and blast-radius treatment

*Security review.* `POST /frbr/relations/merge` performs an irreversible,
unrated, `write:metadata`-gated operation. Since that permission is held by every
contributor, the reachable blast radius is larger than the endpoint's history
suggests.

- Add `@limiter.limit(...)` matching the scan endpoint's posture.
- Merging re-parents `Item` rows **owned by other users** — an intentional
  consequence of consolidating shared catalog data, but it must be visible in the
  audit diff, so `reparented_items` is recorded alongside the other counters.
- Self-merge and cross-tier merge are already refused; both stay refused, and
  the refactor must not introduce a path that skips them.

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Large refactor of shipped 0.8.1 code | `merge_frbr_entities` delegates; signatures and response shape frozen. Rule 9 requires this plan to be approved before implementation. |
| The shared map diverges from the schema again | D3's coverage test is the gate. |
| A future refactor reintroduces `session.delete()` and silently drops contributors | D2 states the Core-level `DELETE` as an invariant and 1.2 tests the source-only contribution shape on PostgreSQL. |
| Expression blocking reintroduces the sibling-collision storm | D5 forbids parent-Work title fallback; a test asserts two Expressions of one Work do not block on each other. |
| Behaviour change for existing manual merges | Strictly additive in safety terms: references that were being destroyed are now preserved. Audit `change_type` values change, which is a query-visible change — noted in the CHANGELOG. |
| `confidence` becomes nullable | Additive migration; existing rows keep their value and are backfilled with `resolution_source='llm'`. |

## Migration plan

Linear, single head, reversible, following the established pattern:

`v0_8_2_duplicate_candidates` → **`v0_8_2_merge_expression_tier`**

- Relax `ck_duplicate_candidates_entity_tier` to include `'expression'`
  (drop + re-add; `ALTER TABLE … DROP CONSTRAINT` then `ADD CONSTRAINT`).
- Add `duplicate_candidates.resolution_source` (`VARCHAR(20)`, NOT NULL,
  server default `'llm'`), then backfill rows that have a non-null
  `llm_reasoning` to `'llm'` and the rest to `'heuristic'`.
- `downgrade()` reverses both and restores NOT NULL on `confidence` only after
  clearing rows whose `confidence IS NULL`, since those rows cannot be
  represented under the previous schema — the downgrade therefore deletes
  heuristic-only candidates rather than failing. This is stated explicitly
  because it is lossy, and it only affects candidates that were never
  human-reviewed.
- `tests/test_migration.py::test_alembic_single_head_and_unbroken_lineage` pins
  the head and the revision walk, so it is updated in the same change.

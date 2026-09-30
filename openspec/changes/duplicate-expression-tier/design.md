## Context

See `proposal.md` for motivation. The state that shapes this approach:

- `frbr-merge-consolidation` (0.8.2) already landed a shared merge core, `app/core/frbr_merge.py`, with a coverage-tested `_EXPRESSION_REFPOINTS` map of seven columns, and declared the Expression-tier requirements in its `frbr/merge-integrity` capability. **This change implements those requirements; it does not redefine them.**
- `duplicate-detection-service` (0.8.2) landed two-stage detection with a deterministic classifier, `classify_pair()`, and an `engine` selector defaulting to `heuristic`.
- The only schema change needed is widening one check constraint. The order-insensitive unique pair index is already keyed on `entity_tier` and is tier-agnostic.
- `v0_8_2_duplicate_provenance` is **already applied** to the preview database.

## Goals / Non-Goals

**Goals:**

- Make the Expression tier reachable through detection and the review queue.
- Preserve the classifier's precision guarantees on a catalog where most Entities sit at F2.
- Keep the candidate card's control count unchanged, so the Expression tier adds no UI density.

**Non-Goals:**

- Not re-specifying anything in `frbr/merge-integrity`; that contract is owned by `frbr-merge-consolidation`.
- Not changing the Work or Manifestation tiers, the classifier's existing rules, or the `heuristic`/`llama` engine split.
- Not adding a per-Expression or per-tier navigation in the review UI.

## Decisions

### D1 — Expression blocking keys are self-referential, with no parent fallback

`Work` and `Manifestation` already inherit the Work's title into their blocking keys, which is why sibling Manifestations of one Work always collide. Expressions would inherit the same defect a full tier higher: **every Expression of a Work shares the Work's title**, so a scan would queue the catalog against itself.

So the Expression tier builds keys from `normalize_title(expression.label)` plus the `(language, content_type)` pair, and the Work title is never consulted.

*Alternative considered:* reuse the Work's title for Expressions but require a creator overlap as a gate. Rejected — it still generates O(n²) same-author pairs per Work, which is exactly the noise the classifier then has to reject one call at a time.

*Subtlety.* An Expression's `label` is optional. Two Expressions of one Work with no labels share only their Work title, which no longer blocks, so they are correctly *not* candidates: with no label and no distinct identity of their own, there is no evidence to act on.

### D2 — Cross-realization pairs are dropped before scoring, not after

A pair differing in `language` or `content_type` is discarded at the blocking stage, before `classify_pair()` runs. This is stricter than rejecting in the classifier: the pair never becomes a candidate, never reaches the report counters, and cannot be queued by either engine.

*Why this matters ontologically.* F2 is a specific realization — a language, a content type. Merging the Polish audiobook of *The Hobbit* with its English print edition would destroy the distinction the hierarchy exists to express, and would silently re-point a `UserWorkIntent.expression_id` that deliberately targeted one translation. The refusal belongs as early as possible.

### D3 — `merge_expression` delegates; it does not reimplement

The new function resolves the tier to `_EXPRESSION_REFPOINTS` and calls the same `repoint_references()` / `delete_source_row()` / audit path as `merge_work` and `merge_manifestation`. Any deviation would reintroduce exactly the class of defect the coverage test in 0.8.2 exists to prevent.

*Alternative considered:* have `merge_work` and `merge_manifestation` dispatch through one generic `merge_entity(tier, ...)`. Tempting, but it would change two already-shipped, already-verified call sites for no behavioural gain, and rule 9 of the implementation guidance prefers the small refactor.

### D4 — One migration, appended, never folded

`ck_duplicate_candidates_entity_tier` is relaxed in place by a new linear revision. Folding it into `v0_8_2_duplicate_provenance` was considered and rejected: that revision is already applied to the preview database, so editing it would make Alembic skip the change there while a fresh install received it — silent schema drift, surfacing later as a constraint violation on the first Expression candidate with nothing pointing at the cause.

*Cost:* one more revision in the 0.8.2/0.8.3 chain. *Benefit:* environments that have already migrated are never silently wrong. The chain stays linear with a single head either way.

### D5 — The candidate card gains a comparison body, not controls

The Expression comparison reuses the existing card. Per the UX audit that shaped 0.8.2, the per-card control count is the thing to protect; a read-only viewer must continue to see one control, not five. So Expression support adds fields to the comparison table and nothing to the action row.

## Risks / Trade-offs

| Risk | Mitigation |
| ---- | ---------- |
| Queue flooding from self-colliding Expressions | D1's no-parent-title-fallback, pinned by a test in task 1.2 before any tier change lands. |
| A merged Expression orphans a user's language-specific wishlist target | `UserWorkIntent.expression_id` is in `_EXPRESSION_REFPOINTS` and is re-pointed, not nulled; covered by the 0.8.2 coverage test and an integrity case. |
| Silent schema drift from an edited applied migration | D4: a new revision, never a modified one. |
| `min_confidence` filtering excludes classifier candidates | Already true for Work/Manifestation since 0.8.2: a NULL confidence fails the `>=` predicate. Documented, not worked around. |
| Reviewers cannot tell an Expression pair from a Work pair at a glance | The `entity_tier` badge is already rendered per candidate; the Expression body makes language and content type explicit. |

## Migration Plan

Linear, single head, reversible: `v0_8_2_duplicate_provenance` → **`v0_8_2_duplicate_expression_tier`**.

- `upgrade()` relaxes `ck_duplicate_candidates_entity_tier` to include `'expression'` (drop and re-add; `ALTER TABLE … DROP CONSTRAINT` then `ADD CONSTRAINT`). No data movement, no table rebuild.
- `downgrade()` restores the two-value constraint. It **fails loudly** if any `expression`-tier candidate exists rather than deleting user-visible review history, so an operator must resolve or explicitly delete those rows first. That is a deliberate choice: the 0.8.2 provenance downgrade deletes NULL-confidence rows because they are unreviewed, but a reviewed candidate is a record of a human decision.
- `tests/test_migration.py::test_alembic_single_head_and_unbroken_lineage` pins both the head and the full revision walk, so it is updated in the same change.

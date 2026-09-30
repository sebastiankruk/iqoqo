## Why

Duplicate detection and merge currently stop at the Work and Manifestation tiers, so a catalog that accumulated two copies of the same realization — the English print edition and its audiobook, or the same film released twice — cannot surface or resolve them through the review queue. Expression (F2) merging *is* already possible by hand via Relation Management, so the gap is discoverability rather than capability: a curator has to know that Expressions live behind a different dialog, and that dialog is reached by browsing rather than by being told where the duplicates are.

Closing it now also becomes materially safer than deferring it further, because the shared merge core landed in `frbr-merge-consolidation` already carries a complete, coverage-tested Expression re-point map. What remains is exposing that path through detection, not building it.

## What Changes

- **Add** the `expression` tier to the `DuplicateCandidate` vocabulary: the check constraint, the model constants, every validation site, the CLI `--tier` choices, and the scan endpoint's `tier` field.
- **Add** `merge_expression` to the duplicate-detection path, delegating to the existing `_EXPRESSION_REFPOINTS` map, so a reviewed Expression pair is consolidated by the same audited core that already serves the manual path.
- **Add** Expression-specific blocking keys derived from the Expression's own identity — normalized label plus the `(language, content_type)` pair — with **no** fallback to the parent Work's title.
- **Add** a hard refusal to merge Expressions whose `language` or `content_type` differ, mirroring the existing F3 rule that different editions are not duplicates.
- **Add** the Expression member to the frontend `DuplicateSide` discriminated union and render an Expression comparison in the existing candidate card, without adding controls.
- **Add** a `Vite`-free, dependency-free migration `v0_8_2_duplicate_expression_tier` relaxing `ck_duplicate_candidates_entity_tier`, linear on the existing single head.
- **Keep** the `heuristic` engine's guarantees: cross-`language` and cross-`content_type` pairs are rejected before scoring, so a catalog with many realizations per Work cannot flood the queue.

## Capabilities

### New Capabilities

None. This change implements behaviour that `frbr-merge-consolidation` already declares; it introduces no new behavior surface of its own.

### Modified Capabilities

- `operations/duplicate-detection`: the candidate entity tier vocabulary widens from `work`/`manifestation` to include `expression`, and screening gains an Expression tier whose blocking keys are self-referential rather than inherited from the parent Work.

### Relationship to `frbr-merge-consolidation`

The Expression-tier *requirements* — the cross-`language`/`content_type` merge refusal, the ban on parent-Work-title blocking keys, and Expression candidates flowing through the review queue — already exist as the `Expression-Tier Merge Safety` requirement in that change's `frbr/merge-integrity` capability. They are deliberately **not** restated here: duplicating them would create two sources of truth for the same contract.

This change therefore **depends on `frbr-merge-consolidation` being archived first**, so that `frbr/merge-integrity` exists in the main specs and this change implements it rather than redefining it.

**That dependency is now discharged, and it makes this change load-bearing.** `frbr-merge-consolidation` was archived on 2026-09-28, publishing `Expression-Tier Merge Safety` into `openspec/specs/frbr/merge-integrity/spec.md`. The main specs therefore now assert that the system supports merging two Expressions, refuses a cross-`language` or `content_type` merge, and screens Expressions on their own identity — **none of which the shipped code does yet**. Until this change is implemented and archived, the specs describe a contract the product does not honour, so this change is no longer merely planned v0.8.3 work: it is the remaining gap between the recorded specification and the running system.

## Impact

- **Backend services:** `app/core/duplicate_service.py` gains `merge_expression`, Expression blocking keys, and tier validation; `app/core/frbr_merge.py` is reused unchanged.
- **Database & models:** `app/db/core.py` widens `DUPLICATE_ENTITY_TIERS`; the check constraint `ck_duplicate_candidates_entity_tier` is relaxed in place. The order-insensitive unique pair index on `(entity_tier, source_id, target_id)` is already tier-agnostic and needs no change.
- **API & routing:** `GET /v1/admin/duplicates` may return `expression`-tier candidates; `POST /duplicates/scan` accepts `tier: "expression"`; `POST /duplicates/<id>/merge` accepts Expression candidates. No new endpoints.
- **CLI:** `scripts/detect_duplicates.py` gains `expression` in `--tier`.
- **Frontend:** the `DuplicateSide` union gains an Expression member; `duplicate-reviewer.tsx` renders language, content type, child Manifestation count and creators. The card's control count is unchanged.
- **Migrations:** one additional linear revision on the existing head. Deliberately *not* folded into `v0_8_2_duplicate_provenance`, which is already applied to the preview database — editing an applied migration silently skips the change there.
- **Dependencies:** none added. Depends on `frbr-merge-consolidation` (0.8.2) for the shared merge core and the declared Expression requirements.
- **Risk:** the widest blast radius of any detection change is queue flooding, since all Expressions of a Work share its title. The no-parent-title-fallback rule is pinned by a test before anything else lands.

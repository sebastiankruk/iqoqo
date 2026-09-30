## Context

Currently, the `UserWorkIntent` object lacks format metadata down the FRBR hierarchy when sent to the frontend. As a result, non-book wishlist items (like Vinyl, Audiobooks, and Board Games) are missing disambiguating properties. The frontend then defaults to text/book badges, which degrades the user experience for mixed-media wishlists. (See proposal.md - Why).

## Goals / Non-Goals

**Goals:**
- Properly extract `work_type` and primary `expression.medium_type` for a given `UserWorkIntent`.
- Expose these attributes in API payloads returning intents (specifically in wishlist serialization).
- Update frontend media badge utilities and item card rendering to reflect polymorphic media types dynamically.

**Non-Goals:**
- Completely rewriting the FRBR mapping structure on the frontend.
- Adding arbitrary new badge icons beyond the currently supported media types.
- Modifying non-intent (regular Item) badge behavior unless intrinsically tied to the same shared utilities.

## Decisions

- **Extracting Data at Serialization**: 
  - We will introduce a serialization helper in `app/core/frbr_service.py` (e.g., `serialize_work_intent_format`) or directly update `app/api/items.py` virtualization logic to query `work.work_type` and traverse down to `expression.medium_type`. Since `UserWorkIntent` primarily holds a reference to a `Work`, we can access `work.work_type`, and iterate its expressions to find a `medium_type` (similar to how `content_type` is extracted).
  - *Alternative*: Denormalize this data onto `UserWorkIntent`. Rejected because it violates our normalized FRBR ontology boundaries and leads to sync issues.
- **Frontend Utility Evolution**: 
  - `frontend/lib/media-badge.ts` will be updated to accept `work_type` and `medium_type` alongside `content_type`.
  - `frontend/components/collection/item-card.tsx` will pass these newly available properties to the badge renderer.

## Risks / Trade-offs

- **Risk: N+1 Query on Expressions/Manifestations** → Traversing `work.expressions` for multiple `UserWorkIntents` can lead to N+1 queries.
  - *Mitigation*: Ensure that the queries fetching `UserWorkIntent` in `app/api/items.py` use appropriate eager loading (e.g., `joinedload(UserWorkIntent.work).joinedload(Work.expressions)`) if not already present, or rely on existing optimized data extraction paths.
- **Risk: Multiple Expressions/Manifestations with differing media types** → A Work could technically have multiple expressions with different `medium_type`.
  - *Mitigation*: Fall back to a "primary" expression logic (e.g., taking the first expression, which matches current `content_type` extraction logic), as intents are often added against a top-level work before a specific manifestation is selected.

## Context

See proposal.md - Why.
Currently, collection item cards in `frontend/components/collection/` display cover, title, author, and format, linking exclusively to the physical copy (`/item/[id]`) or edition (`/manifestation/[id]`). The FRBR conceptual levels (Work and Expression) exist as full Next.js App Router routes (`/work/[id]` and expression data structures), but are not easily discovered or navigated from collection browse views.

## Goals / Non-Goals

**Goals:**
- Provide clear, non-intrusive clickable navigation affordances on collection item cards to parent Work and Expression views.
- Render explicit FRBR hierarchy breadcrumbs on Item detail views.
- Ensure all collection payload projections include `work_id` and `expression_id` to eliminate frontend fetch cascades.

**Non-Goals:**
- Creating a separate collection view solely for standalone Work entities (deferred to future milestone).
- Modifying backend FRBR persistence or relationship constraints.

## Decisions

1. **Breadcrumb / Chip Link Placement:**
   - On collection item cards, render subtle parent chips or title sub-links (`Work: <title>`) that open the Work page directly.
   - On Item detail header, provide a breadcrumb trail: `Home / Collection / Work / Expression / Manifestation / Item`.
2. **Payload Enrichment:**
   - Ensure `app/api/items.py` and `app/api/collections.py` include `work_id`, `work_title`, and `expression_id` in item serialization summaries.
   - Fall back gracefully when an item is orphan or manifestation lacks work binding.

## Risks / Trade-offs

- [Risk] Card UI clutter from too many nested links → [Mitigation] Keep main card click target on Item, with Work link styled as a secondary discrete text link/badge.
- [Risk] Missing work_id on legacy items → [Mitigation] Conditional rendering: only render Work link when `work_id` is present.

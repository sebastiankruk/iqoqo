## Context

See `proposal.md` for motivation. During the `/grill-me` design review (`2026-11-18`), removing the `"Federation Coming Soon"` tab entirely (rather than inventing a duplicate federation tab) was chosen because item ownership, lending custody (`sidebar-lending-info.tsx`), and federation controls already live in the sidebar and `/federation/directory` / `/admin/federation`. Simultaneously, `principal-review-release-1.0.3.md` identified 13 legacy `.query` calls in `app/api/items.py` (`lines 82, 88, 367, 543, 994, 1025, 1036, 1100, 1125, 1129, 1205, 1621, 1823`).

## Goals / Non-Goals

**Goals:**
- Eliminate `"Federation Coming Soon"` dead UI from `frontend/components/item/item-tabs.tsx` while keeping federated loan/provenance visibility in `DetailsTab`.
- Bring `app/api/items.py` to 100% SQLAlchemy 2.0 `select()` compliance.

**Non-Goals:**
- Building a standalone ActivityPub activity timeline inside `ItemTabs` (covered by existing `ItemProvenanceTimeline` and `/federation/directory`).

## Decisions

1. **Remove `FederationTab` from `TABS` and surface badge in `DetailsTab`:** Avoids an extra tab click for rare metadata while immediately resolving the misleading `"Federation Coming Soon"` bug.
2. **Mechanical SQLAlchemy 2.0 `select()` conversion in `app/api/items.py`:** Replace `db.session.query(...)` and `Model.query.filter_by(...)` with `db.session.execute(select(...)).scalars().all()` / `.scalar_one_or_none()` / `.scalar()`, keeping `func.count(...) # pylint: disable=not-callable` per project standards.

## Risks / Trade-offs

- **Subtle scalar vs tuple differences during `.query` migration** → Run the complete existing item API Pytest suite (`tests/test_api_items*.py`, `tests/test_item_*.py`) and static check asserting zero `.query` occurrences in `app/api/items.py`.

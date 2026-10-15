## Why

In complex bibliographic collections, individual Works frequently belong to more than one series simultaneously (e.g. an overarching universe series like "Cosmere" and a sub-series like "Mistborn", or shared franchise crossovers). Currently, Work models and the FRBR Editor only support a single parent container / series pointer, preventing collectors and custodians from recording multi-series memberships and showing visual series badges on Work/Item pages. Addressing this in `v0.8.4` fulfills dev-note item `#v084` ("Support for series - one work (?) should be able to belong to multiple series, we need visual UI hint showing this, and FRBR editor should support custodians in doing that.").

## What Changes

- Model multi-series memberships via a many-to-many relationship (`WorkSeriesMembership`) associating Works with series container Works along with sequence positions.
- Update the FRBR Editor (`frontend/components/editor/`) to allow custodians to add, reorder, and remove multiple series memberships for a Work.
- Display visual UI badges and breadcrumb hints on Work and Item detail pages for all linked series.

## Capabilities

### Modified Capabilities
- `editor/relation-management`: Add multi-series container membership management for Works, allowing assignment to multiple series with distinct ordinal sequence positions.

## Impact

- `app/db/models.py`: Add `WorkSeriesMembership` association model and migration.
- `app/api/frbr.py`: Update Work serialization and relations endpoints.
- `frontend/components/editor/`: Support adding/removing multiple series in the FRBR Editor.
- `frontend/components/item/item-tabs.tsx` & `components/work/`: Render badges for all series memberships.

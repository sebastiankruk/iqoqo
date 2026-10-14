## 1. UI Tag Cloud Component

- [x] 1.1 Create `TagCloud` component with `maxInitial` folding, smooth disclosure toggle ("+X more" / "Show less"), and tooltip display for source provenance.
- [x] 1.2 Replace raw tag mappings in `manifestation-detail-client.tsx` and `item-tabs.tsx` with `<TagCloud>`.

## 2. Provenance Metadata Exposure

- [x] 2.1 Update backend serialization in `app/api/manifestations.py` to preserve source attribute on tags when present.

## 3. Verification

- [x] 3.1 Add Vitest tests verifying `TagCloud` renders compact list and expands on click.

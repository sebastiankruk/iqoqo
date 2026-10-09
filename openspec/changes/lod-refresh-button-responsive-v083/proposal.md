## Why

On the Manifestation and Item pages, the Linked Open Data (LOD) panel's "Scan External LOD" trigger button overflows its visual button container when rendered on narrow viewports or under languages with longer translated strings (such as Polish "Skanuj zewnętrzne LOD"). Furthermore, users inspecting their individual Item copies lack visibility into the resolved Linked Open Data entities inherited from the parent Manifestation without navigating away to the Manifestation catalog entry. 

Standardizing responsive layout constraints on the `SemanticLinks` header and exposing inherited LOD entities on Item detail views resolves dev-note item `#v083 #ux #bug` ("LOD refresh buttons on Item/Manifestation page have label going out of button frame").

## What Changes

- Modify `frontend/components/manifestation/semantic-links.tsx` header layout to use responsive flex wrapping (`flex-col sm:flex-row sm:items-center justify-between gap-3`), preventing button clipping on narrow cards and localized strings.
- Ensure the LOD scan button retains accessible truncated text labels with full tooltip titles (`title={t("scanButton")}`) and flex shrink safety.
- Mount `SemanticLinks` within the Item detail view (`frontend/components/item/item-tabs.tsx` under the Details tab) when `item.manifestation_id` is present, allowing copy custodians to inspect and trigger LOD enrichment directly from their holding view.

## Capabilities

### Modified Capabilities
- `semantic/lod-linking`: Extend the UI requirements to ensure Linked Open Data panels support responsive button constraints preventing text overflow, and expose inherited Manifestation semantic links within Item detail views.

## Impact

- `frontend/components/manifestation/semantic-links.tsx`: Responsive header layout and button containment.
- `frontend/components/item/item-tabs.tsx`: Embed `SemanticLinks` card under Item Details view.
- `frontend/__tests__/components/manifestation/semantic-links.test.tsx` & item tests: Add assertions for responsive button rendering and Item LOD mounting.

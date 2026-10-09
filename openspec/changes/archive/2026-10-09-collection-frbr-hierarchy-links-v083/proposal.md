## Why

Dev-note item (#ux #v083): "add links to Work and Expression pages from the collection views". Release planning: v0.8.x, C55 (target v0.8.3).

Premises verified against code:
- **Confirmed: Direct card navigation targets Item/Manifestation only.** In `frontend/components/collection/item-card.tsx:128,306,394`, cards wrap the entire tile in `<Link href={targetHref}>` targeting `/item/[id]` or `/manifestation/[id]`.
- **Confirmed: Entity data already includes Work and Expression.** The `Item` TypeScript definition (`frontend/types/frbr.ts:225-226`) and collection API responses already provide `item.work` (`{ id, title, authors }`) and `item.expression` (`{ id, content_type, language }`). No new backend queries or N+1 additions are needed.
- **Confirmed: Routes exist.** Frontend routes `frontend/app/work/[id]` and `frontend/app/expression/[id]` already exist in the Next.js App Router.
- **Technical Constraint: Nested HTML anchors.** Because `item-card.tsx` wraps the card in Next.js `<Link>`, inserting child `<Link>` components violates HTML specifications (`<a> cannot appear as a descendant of <a>`). Navigation to Work and Expression must use explicit event handling, card action areas, or decoupling card surface clicks.

## What Changes

- **Collection Card FRBR Breadcrumb / Links:** In `frontend/components/collection/item-card.tsx` (both horizontal and grid variants), provide subtle badges or secondary navigation links to `/work/[id]` and `/expression/[id]` without generating invalid nested anchor tags.
- **Item Header Breadcrumbs:** In `frontend/components/item/item-header.tsx`, ensure clear navigable FRBR breadcrumbs (`Work > Expression > Manifestation > Item`) are rendered prominently.
- **Accessible Navigation:** Preserve keyboard accessibility and screen-reader navigable labels for all entity tiers.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None (`skip_specs: true` has been set).

## Impact

- **Frontend:** `frontend/components/collection/item-card.tsx`, `frontend/components/item/item-header.tsx`.
- **Backend:** Zero changes (API already returns nested FRBR metadata).
- **Tests:** Vitest component tests verifying that clicking Work and Expression pills triggers navigation to `/work/:id` and `/expression/:id` respectively, and asserting absence of nested `<a>` elements in the DOM.

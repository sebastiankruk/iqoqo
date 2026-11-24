## Why

While `C142` (`item-page-ux-declutter-and-graph-entry-v112`) resolves `"Explore Graph"` placement and localization on `/item/[id]`, an `iqoqo-ux-auditor` audit across the remaining FRBR Group 1 entity detail pages (`/work/[id]`, `/expression/[id]`, and `/manifestation/[id]`) reveals inconsistent button placement, mobile above-the-fold pushdown, and hardcoded English labels:
1. `/work/[id]` (`work-detail-client.tsx`) places `"Explore Graph"` inside the hero metadata action cluster between `"Add Issue"` and `"Add to Wishlist"` below a `256px` mobile cover, crowding the action row and hardcoding `"Explore Graph"`.
2. `/manifestation/[id]` (`manifestation-detail-client.tsx`) has no top utility bar and places `"Explore Graph"` (`ml-auto`) in the metadata badge strip below a tall `aspect-[2/3]` mobile cover (pushing it near or below the `390x844` fold) with hardcoded `"Explore Graph"`.
3. `/expression/[id]` (`expression-detail-client.tsx`) already places `"Explore Graph"` cleanly in the top utility bar next to `[← Back]`, but hardcodes `"Explore Graph"` instead of using the existing `graph.exploreGraph` translation key (`"Explore Graph"` / `"Eksploruj graf"`).

## What Changes

- **Unify `"Explore Graph"` placement in a consistent top utility bar across `/work/[id]`, `/expression/[id]`, and `/manifestation/[id]`:**
  - **`/work/[id]` (`frontend/components/work/work-detail-client.tsx`):** Move the secondary `"Explore Graph"` button (`data-testid="explore-graph-link"`, `variant="outline"`, `size="sm"`) from the hero metadata action cluster into the existing top utility bar alongside `[← Back]` and the `FRBR Work #id` badge (`hidden sm:inline-flex` on extra-narrow viewports so `360px`–`390px` never wraps awkwardly). This frees the hero action row for primary work actions (`Add Issue` / `Add to Wishlist`) and guarantees `"Explore Graph"` is above the fold on mobile (`390x844`) and desktop (`1280x800`).
  - **`/manifestation/[id]` (`frontend/components/manifestation/manifestation-detail-client.tsx`):** Add the matching lightweight top utility bar (`border-b border-border/60 bg-muted/20`) with `[← Back]` on the left and `"Explore Graph"` (`data-testid="explore-graph-link"`, `variant="outline"`, `size="sm"`) + compact `FRBR Manifestation #id` badge (`hidden sm:inline-flex`) on the right, removing the displaced button from the metadata badge strip below the mobile cover.
  - **`/expression/[id]` (`frontend/components/expression/expression-detail-client.tsx`):** Preserve its existing top utility bar placement for `"Explore Graph"` (`data-testid="explore-graph-link"`), add responsive badge compaction (`hidden sm:inline-flex` on `FRBR Expression #id`) for `360px`–`390px` viewports, and localize the label.
- **Eliminate hardcoded `"Explore Graph"` strings across all FRBR detail views:**
  - Wire `useTranslations("graph")("exploreGraph")` in `WorkDetailClient`, `ExpressionDetailClient`, and `ManifestationDetailClient` (coordinating with `C142`, which wires `graph.exploreGraph` in `ItemHeader`), ensuring 100% English (`"Explore Graph"`) and sentence-case Polish (`"Eksploruj graf"`) parity.
- **Preserve static export & existing navigation contracts:**
  - Keep query-parameter links (`/graph?type=work&id=...`, `/graph?type=expression&id=...`, `/graph?type=manifestation&id=...`) compatible with `CAPACITOR_BUILD=true` static export and preserve `data-testid="explore-graph-link"` across all entity pages.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `visual-frbr-relation-graph`: Add a requirement standardizing above-the-fold top-utility-bar placement, `<= 4` button-density compliance, and `graph.exploreGraph` localization for `"Explore Graph"` entry buttons across `/work/[id]`, `/expression/[id]`, and `/manifestation/[id]` (coordinating cleanly with `C142`'s `/item/[id]` requirement via `## ADDED Requirements`).

## Impact

- **Frontend UI:** `frontend/components/work/work-detail-client.tsx`, `frontend/components/expression/expression-detail-client.tsx`, `frontend/components/manifestation/manifestation-detail-client.tsx`.
- **Frontend Localization:** Uses existing `graph.exploreGraph` key in `frontend/messages/en.json` and `frontend/messages/pl.json` (plus `common.back` or existing back label parity if localized).
- **Tests:** `frontend/__tests__/components/work/work-page.test.tsx`, `frontend/__tests__/components/expression/expression-seo.test.tsx`, `frontend/__tests__/components/manifestation/manifestation-wishlist.test.tsx` (or dedicated entity graph-entry Vitest tests), and `frontend/__tests__/e2e/relation_graph.spec.ts` / `frontend/__tests__/e2e/ux_audit.spec.ts`.
- **Backend / FRBR Schema Impact:** Zero backend or database changes; preserves four-tier FRBR entity routing (`Work -> Expression -> Manifestation -> Item`).

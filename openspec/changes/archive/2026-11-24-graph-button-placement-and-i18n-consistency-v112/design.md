## Context

See `proposal.md` for motivation. Across the four FRBR Group 1 entity detail views:
- `/item/[id]` is already redesigned by `C142` (`item-page-ux-declutter-and-graph-entry-v112`), placing localized `"Explore Graph"` (`graph.exploreGraph`) above the fold in `ItemHeader`.
- `/expression/[id]` (`frontend/components/expression/expression-detail-client.tsx:125-149`) already places `"Explore Graph"` in a clean top utility bar (`border-b border-border/60 bg-muted/20`), but hardcodes `"Explore Graph"` instead of using `useTranslations("graph")("exploreGraph")`.
- `/work/[id]` (`frontend/components/work/work-detail-client.tsx:189-294`) has the same top utility bar, but places `"Explore Graph"` inside the hero metadata action cluster below the `256px` mobile cover, competing with `"Add Issue"` and `"Add to Wishlist"`, and hardcodes `"Explore Graph"`.
- `/manifestation/[id]` (`frontend/components/manifestation/manifestation-detail-client.tsx:234-340`) lacks a top utility bar completely and renders `"Explore Graph"` (`ml-auto`) in the metadata badge strip below a full-width `aspect-[2/3]` mobile cover (pushing it near/below the `390x844` fold) with hardcoded `"Explore Graph"`.

Both `frontend/messages/en.json:1210` (`"exploreGraph": "Explore Graph"`) and `frontend/messages/pl.json:1210` (`"exploreGraph": "Eksploruj graf"`) already define `graph.exploreGraph`.

## Goals / Non-Goals

**Goals:**
- Establish one predictable, `iqoqo-ux-auditor`-compliant top utility bar across `/work/[id]`, `/expression/[id]`, and `/manifestation/[id]` so `"Explore Graph"` is always 1 tap away above the fold on mobile (`390x844`) and desktop (`1280x800`).
- Remove all hardcoded `"Explore Graph"` strings in `WorkDetailClient`, `ExpressionDetailClient`, and `ManifestationDetailClient` in favor of `useTranslations("graph")("exploreGraph")`.
- Prevent `360px`–`390px` mobile header wrapping by hiding the decorative `FRBR <Tier> #id` badge below `sm` (`hidden sm:inline-flex`).
- Compose cleanly with `C142` (`/item/[id]`) and `C143` (multi-root `/graph` picker) with zero spec or component merge conflicts.

**Non-Goals:**
- Modifying `/item/[id]` (`ItemHeader` is owned by `C142`).
- Modifying `/graph` itself or backend `GET /api/catalog/graph` (owned by `C143`).
- Restructuring the main content sections of `/work/[id]`, `/expression/[id]`, or `/manifestation/[id]` beyond the top utility bar and removing the displaced `"Explore Graph"` button.

## Decisions

### 1. Standardized Top Utility Bar Pattern Across Work, Expression, and Manifestation
- **Decision:** Adopt `/expression/[id]`'s lightweight top utility bar (`border-b border-border/60 bg-muted/20`) as the canonical header strip across `/work/[id]`, `/expression/[id]`, and `/manifestation/[id]`:
  - Left: `[← Back]` (`variant="ghost"`, `size="sm"`, `router.back()`).
  - Right: `[Explore Graph]` (`data-testid="explore-graph-link"`, `variant="outline"`, `size="sm"`, `<GitBranch className="h-3.5 w-3.5" />`, `tGraph("exploreGraph")`) + `[FRBR <Tier> #<id>]` badge (`hidden sm:inline-flex`).
- **Alternatives Considered:**
  - *Alternative A — Place `"Explore Graph"` inside the hero badge row on all 3 pages:* Rejected because on mobile (`< md`), `/work/[id]` and `/manifestation/[id]` render tall cover artwork above the metadata column, pushing `"Explore Graph"` below the fold (`y > 600px–800px` on `390x844`) and crowding serial `"Add Issue"` / `"Add to Wishlist"` CTAs.
  - *Alternative B — Add a floating FAB on mobile for `"Explore Graph"`:* Rejected because floating action buttons obstruct bottom navigation (`[Home | Collection | Scan | Profile]`) and violate secondary-action visual hierarchy (`iqoqo-ux-auditor`).

### 2. Coordination with `C142` and `C143`
- **Decision:** Scope `C149`'s delta spec under `## ADDED Requirements` in `visual-frbr-relation-graph` rather than `## MODIFIED` on `C142`'s requirement block, and touch only `work-detail-client.tsx`, `expression-detail-client.tsx`, and `manifestation-detail-client.tsx`.
- **Rationale:** Guarantees zero git/OpenSpec merge conflicts regardless of whether `C142`, `C143`, or `C149` is applied first on `release/1.1.2`.

## Full-Page DOM Layout Snapshot (`390x844` Mobile)

```text
/work/[id] BEFORE                             /work/[id] AFTER
-------------------------------------------   -------------------------------------------
1. Navbar                                     1. Navbar
2. Top Bar: [<- Back]        [FRBR Work #1]   2. Top Bar: [<- Back]       [Explore Graph]
3. Hero Cover (256px tall)                       (FRBR Work #1 hidden < sm; <= 2 buttons)
4. Metadata Header (pushed down!)             3. Hero Cover (256px tall)
   - Badges + [Add Issue] [Explore Graph]     4. Metadata Header
     [Add to Wishlist] (crowded wrap!)           - Badges + [Add Issue] [Add to Wishlist]

/manifestation/[id] BEFORE                    /manifestation/[id] AFTER
-------------------------------------------   -------------------------------------------
1. Navbar                                     1. Navbar
2. Cover Art (aspect 2/3, ~510px tall!)       2. Top Bar: [<- Back]       [Explore Graph]
3. Metadata Column (near/below fold!)            (FRBR Manifestation #1 hidden < sm)
   - Badges + [Explore Graph (ml-auto)]       3. Cover Art + Metadata Column
                                                 - Badges (clean, no displaced button)

/expression/[id] BEFORE                       /expression/[id] AFTER
-------------------------------------------   -------------------------------------------
1. Navbar                                     1. Navbar
2. Top Bar: [<- Back] [Explore Graph*]        2. Top Bar: [<- Back]       [Explore Graph]
   [FRBR Expression #1] (*hardcoded EN)          (localized graph.exploreGraph; badge sm+)
```

## Interaction Friction Map (Entity Page → Visual Graph)

1. **Tap 1:** Tap `data-testid="explore-graph-link"` (`Explore Graph` / `Eksploruj graf`) in the top utility bar (immediately visible above the fold on mobile and desktop).
- **Total Taps:** `1` (`<= 3` target PASS). Identical spatial muscle memory across `/work/[id]`, `/expression/[id]`, and `/manifestation/[id]`.

## Risks / Trade-offs

- **[Existing unit/E2E tests mocking `next-intl` without `graph` namespace in `ExpressionDetailClient` / `WorkDetailClient` / `ManifestationDetailClient`]** → Mitigated by checking existing Vitest test setups (`work-page.test.tsx`, `expression-seo.test.tsx`, `manifestation-wishlist.test.tsx`) and ensuring `next-intl` test mocks/providers include `graph.exploreGraph`.
- **[Extra top bar height on `/manifestation/[id]` (~52px)]** → Mitigated by adjusting the main container's top padding (`py-8 sm:py-10` instead of `py-12`) so desktop vertical balance stays compact and cover art remains comfortably visible above the fold.

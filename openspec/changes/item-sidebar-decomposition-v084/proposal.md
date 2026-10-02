## Why

`frontend/components/item/item-sidebar.tsx` is **838 lines and contains exactly one React component**, whose `return` statement spans roughly 550 of them (lines 300–838). C18 task 3.9 named this decomposition (MOD-FE_UI-18) and deferred it with the note: *"Unaudited — decompose only if it yields a real seam."*

Audited 2026-10-02. The seam is real but **smaller than the line count implies**, and the honest finding is that this is a *readability* change, not a defect fix. That framing matters, because every other change carried by C18 has a demonstrated bug behind it and this one does not — it is worth doing for maintainability, and should be judged as such rather than smuggled in alongside bug fixes as if it were one.

**What the audit found:**

- **The component is not stateful in a way that causes bugs.** Six `useState` calls, one `useEffect`, two props (`item`, `onEdit`). There is no state machine and no lifecycle coupling to untangle — the usual reasons a long component actually misbehaves are both absent.
- **The cost is one enormous JSX block.** Six commented sections are already marked inline: cover, status badges, lending info, ISBN, action buttons and status selects, and FRBR quick info. Those markers *are* the seam. The refactor is mostly lifting already-labelled regions into named components.
- **`PrintQrCodeDialog` is a plain static import (line 51), not lazy.** An earlier draft of this proposal asserted it was `dynamic()`-loaded and that hoisting it would bloat the bundle. That was wrong — it was checked while writing this file rather than assumed, and `qrcode-dialog.tsx` pulls in nothing heavier than `lucide-react` icons and the shared `apiClient`, both already on the item page's path. **There is no bundle-size trap here.** The correction matters: a design built around a hazard that does not exist would add a constraint and a test for nothing.
- **`item-sidebar-media-filtering.test.tsx` and `item-sidebar.test.tsx` exist**, so the extraction has regression coverage of behaviour. What they do *not* cover is structural: nothing asserts that a given region's markup still renders, so a region lifted into a component that silently returns `null` would pass both files.

## What Changes

- Extract the six already-commented JSX regions of `ItemSidebar` into sibling components under `frontend/components/item/sidebar/`:
  - `sidebar-cover.tsx` — cover art with the Book/Audio branch
  - `sidebar-status-badges.tsx` — status and collection-status badges
  - `sidebar-lending-info.tsx` — borrower / loan state
  - `sidebar-identifiers.tsx` — ISBN and other identifiers
  - `sidebar-actions.tsx` — action buttons and the status selects
  - `sidebar-frbr-info.tsx` — the FRBR quick-info panel
- Each extracted component receives explicit props. **No new context, no new provider, and no shared mutable state object** — the current two props plus the handful of mutation callbacks each region already closes over are sufficient, and passing a mutable "everything" bag would preserve the coupling while hiding it.
- `PrintQrCodeDialog` moves into `sidebar-actions.tsx` as the static import it already is. No code-splitting change.
- The mutation hooks and the handlers that wrap them (eleven `const handle*` definitions, lines 147–296) are lifted into one `useItemSidebarActions(item)` hook rather than passed down individually, so each region's props stay small and the toast wording lives in one place instead of being duplicated across six files.
- No behavioural change. No API change. No schema change.

## Capabilities

### New Capabilities

None. This is a pure internal refactor: no requirement, observable behaviour, or interface changes.

### Modified Capabilities

None. Per the schema's own guidance, a change with no spec-level behaviour change sets `skip_specs: true` in `.openspec.yaml` rather than inventing a requirement to satisfy validation.

## Impact

**Affected code**

- `frontend/components/item/item-sidebar.tsx` — 838 lines → an orchestrator of roughly 180–220 lines.
- `frontend/components/item/sidebar/` — seven new files (six presentational, one hook).
- `frontend/app/item/[id]/page.tsx` — **must not change.** `ItemSidebar`'s signature is `({ item, onEdit })` and stays exactly that, so the page is untouched.

**Tests**

- Existing: `frontend/__tests__/components/item/item-sidebar.test.tsx`, `item-sidebar-media-filtering.test.tsx`.
- **New: per-region render assertions.** The existing suites exercise the sidebar through the orchestrator, so a region extracted into a component that renders nothing would not be caught. Each new component gets a focused test asserting its distinguishing content — the lending region shows a borrower, the identifiers region shows an ISBN, and so on.

**Explicitly not affected**

- No API, no database, no migration, no backend test changes.
- No bundle-size change, and therefore no performance claim to verify.
- `frontend/lib/meta.ts` (C18 3.10) is read by these regions and is unchanged by this work.

**Risk**

Low. The two real hazards are **hook ordering** (moving a `useState`/`useEffect` across a component boundary changes when it runs) and **silent region loss** (a lifted block that returns `null` still passes the orchestrator-level tests). The first is caught by the existing suites, which render the whole sidebar; the second needs the new per-region tests.
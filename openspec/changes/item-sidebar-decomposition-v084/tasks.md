> **Scope discipline.** This is a pure refactor with no defect behind it (see `proposal.md` — Why). Every task must leave behaviour byte-identical: same class names, same DOM order, same conditional expressions, same toast wording. If a task is tempted to "improve" something it encounters, that belongs in a separate change.
>
> **One region per commit.** The task list is deliberately sequenced as single-region extractions so that any regression is attributable to one commit and revertible without unwinding the rest. Do not batch two regions into one commit even when they look similar.
>
> **The invariant check.** After every extraction, `item-sidebar.test.tsx` and `item-sidebar-media-filtering.test.tsx` must pass **unmodified**. Those two files are what prove no behaviour moved; a failure means a region was lifted incorrectly, not that a test needs updating.

## 1. Foundation

- [ ] 1.1 Add `frontend/__tests__/components/item/sidebar-baseline.test.tsx` capturing the *current* rendered regions of `ItemSidebar` — cover branch, status badges, lending info, ISBN, action buttons and status selects, FRBR quick info — asserting each region's distinguishing text. **This is written BEFORE any extraction and must pass against the unmodified 838-line component.** Verify: the new file passes on the untouched `item-sidebar.tsx`. It is the regression net for every later task, and it is worthless if written after the fact because it would encode whatever the refactor happened to produce.
- [ ] 1.2 Confirm the pre-refactor baseline: run `npx vitest run __tests__/components/item/item-sidebar.test.tsx __tests__/components/item/item-sidebar-media-filtering.test.tsx __tests__/components/item/sidebar-baseline.test.tsx` and `npm run type-check`. Verify: all green and type-check clean before any edit. Record the test count — a later task that changes it is telling you something.

## 2. Extract the handler prologue

- [ ] 2.1 Create `frontend/components/item/sidebar/use-item-sidebar-actions.ts` moving lines 147–296 verbatim: `handleUploadComplete`, `addToCollection`, `handleAddToCollection`, `handleRemoveFromCollection`, `handleRequestLoan`, `handleStatusChange`, `handleCollectionStatusChange`, `handleLentSubmit`, `handleToggleVisibility`, plus the `useUpdateItem` / `useAddItemToCollection` hooks they use. **Return a named object, never a positional tuple** (design decision 2). `ItemSidebar` calls the hook and destructures. Verify: `item-sidebar.test.tsx` and `item-sidebar-media-filtering.test.tsx` pass unmodified; type-check clean; `git diff -w` on the moved block shows no logic changes, only indentation.

## 3. Extract the regions — one per task

Each task: create the component with explicit props (design decision 3), replace the inline JSX block with the component, then run the full item-component suite plus type-check before committing.

- [ ] 3.1 Extract the cover region (`// Book/Audio cover`, line ~301) to `frontend/components/item/sidebar/sidebar-cover.tsx`. **The `format` value is computed in the prologue at lines 123–125, not in the region**, and is *already correct*: it reads `manifestation_meta["format"] ?? meta["format"] ?? "book"` — two different **sources**, not two casings. That is a legitimate precedence order and `readMeta()` from C18 3.10 does **not** model it (it takes one object and tries key spellings within it). **Pass `format` and the four derived booleans down as props; do not "fix" this into a `readMeta` call.** Verify: baseline test's cover-branch assertion passes; existing two suites unmodified; `git diff -w` shows the `format`/`isAudio`/`isVideo`/`isGame`/`isBook` lines untouched.
- [ ] 3.2 Extract the status badges region (line ~324) to `sidebar-status-badges.tsx`. Verify: baseline assertion passes; existing suites unmodified.
- [ ] 3.3 Extract the lending-info region (line ~351) to `sidebar-lending-info.tsx`. This region closes over `handleRequestLoan` and `handleLentSubmit` — pass them as props from the hook. Verify: baseline assertion passes; existing suites unmodified.
- [ ] 3.4 Extract the ISBN/identifiers region (line ~367) to `sidebar-identifiers.tsx`. Audited 2026-10-02: this region reads only `item.isbn` and has **no** `meta` fallback chain, so there is nothing to convert to `readMetaChain` — `grep -nE 'meta\[' components/item/item-sidebar.tsx` returns four hits (lines 106, 110, 124, 317), none of them in the identifiers region. **Do not add one.** Verify: baseline assertion passes; existing suites unmodified; no `meta[` access appears in the new file.
- [ ] 3.5 Extract the actions region (`// Action buttons & Status Selects`, line ~370–739 — the largest block) to `sidebar-actions.tsx`. `PrintQrCodeDialog` moves here as the **static import it already is** (design decision 4 — do not introduce a `dynamic()` boundary). This region also carries `handleUploadComplete`. Verify: baseline assertion passes; existing suites unmodified; `grep -n "dynamic(" components/item/sidebar/sidebar-actions.tsx` returns nothing.
- [ ] 3.6 Extract the FRBR quick-info region (line ~740) to `sidebar-frbr-info.tsx`. Verify: baseline assertion passes; existing suites unmodified.

## 4. Per-region unit tests

- [ ] 4.1 Add `frontend/__tests__/components/item/sidebar/` tests, one per extracted component, each rendering the component **directly from a plain props object** — no hook, no provider, no router (this is what design decision 3 buys). Assert each region's distinguishing content. Verify: all pass; and confirm the direct-render shape by checking one test contains no `QueryClientProvider` and no `useItemSidebarActions`.
- [ ] 4.2 Assert the deliberate non-goals. Add a check that no extracted component imports `useItemSidebarActions` (regions take props, not the hook), and that no region opens a context provider. Verify: a grep-based test or lint assertion passes — these encode the design decision so a later contributor cannot quietly reintroduce the coupling.

## 5. Final verification

- [ ] 5.1 Run the complete frontend suite (`npm run test`) and `npm run type-check`, plus `npx eslint components/item/item-sidebar.tsx components/item/sidebar/` and `npx prettier --check` on the same paths. Verify: all green, zero new warnings. The pre-existing 1,255-test count and the two `no-unused-vars` warnings in `frbr-editor.test.tsx` must be unchanged — a changed count means a region lost behaviour.
- [ ] 5.2 Confirm the public signature is unchanged: `git diff frontend/app/item/[id]/page.tsx` must be **empty**. Verify: that diff is empty. If it is not, the refactor leaked into the page's contract and the design's Non-Goals were broken.
- [ ] 5.3 Confirm no performance claim is being made falsely: verify the file count and sizes (`item-sidebar.tsx` should be roughly 180–220 lines, each new component well under 200) and that no `dynamic()` import was introduced anywhere in `components/item/sidebar/`. Verify: line counts as expected and `grep -rn "dynamic(" components/item/sidebar/` returns nothing.

## 6. Close the C18 task

- [ ] 6.1 Mark C18 task **3.9** complete in `openspec/changes/moderate-findings-sweep/tasks.md`, recording that MOD-FE_UI-12 was already done (2026-10-01) and MOD-FE_UI-18 is delivered by this change, with the final component list and test counts. Verify: C18's count increments from 30/48 to 31/48 and the entry cites this change by name rather than claiming the work inline.
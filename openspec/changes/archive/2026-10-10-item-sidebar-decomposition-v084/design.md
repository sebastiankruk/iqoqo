## Context

`ItemSidebar` is a single 838-line component whose `return` spans lines 300–838. See `proposal.md` for why this is being decomposed and for the audit that scoped it. What constrains the *approach* is this:

- **Six `useState` calls and one `useEffect`, all before line 300.** Every piece of local state is declared in a ~200-line prologue; the remaining ~540 lines are pure JSX. That split is the whole opportunity — the prologue is already a coherent unit and the JSX is already marked into six named regions by inline comments (`// Book/Audio cover`, `// Status badges`, `// Lending info`, `// ISBN`, `// Action buttons & Status Selects`, `// FRBR quick info`).
- **Eleven `const handle*` definitions occupy lines 147–296**, interleaved with the hooks they use. They are the shared surface between regions: the status selects, the lending form, the visibility toggle and the collection actions all live here.
- **Public signature is two props** — `{ item: Item; onEdit?: () => void }` — and is consumed by `frontend/app/item/[id]/page.tsx`.
- **`frontend/lib/meta.ts` (C18 3.10) exists and could be mistaken for a required input here.** It does not apply to this component: its only `meta` reads are `manifestation_meta["cover_url"]`, `manifestation_meta["format"] ?? meta["format"] ?? "book"`, and `manifestation_meta["cover_source"]`. The second is a precedence order across two *sources*, which `readMeta()` — one object, several key spellings — does not model. All three are already correct and are copied verbatim. **The refactor must not introduce a `readMeta` call here**, and a reviewer seeing one should treat it as a behaviour change.
- **`PrintQrCodeDialog` is a static import** (line 51) whose own dependencies are `lucide-react` icons, `sonner`, and the shared `apiClient` — all already on this page's path. An earlier draft of the proposal claimed it was `dynamic()`-loaded; it is not, and no bundle-size concern applies.

## Goals / Non-Goals

**Goals:**

- Make the sidebar reviewable in the same units a reviewer thinks in — cover, badges, lending, identifiers, actions, FRBR info — by making those units the actual component boundaries.
- Keep each extracted component's props a short, explicit list, so what a region needs is legible at its signature.
- Leave `ItemSidebar`'s public signature and the page that renders it untouched.
- Preserve observable behaviour exactly, including toast wording, ordering, and conditional rendering.

**Non-Goals:**

- **Not a performance change.** No lazy loading, no memoisation, no render-count optimisation. The component is not slow; it is long.
- **Not a state-management migration.** No context, no reducer, no external store. Introducing one would be a larger change than the one being asked for.
- **Not a styling or markup change.** Class names, DOM order and conditional expressions are copied verbatim. Where a region reads `meta`, it reads it via `lib/meta.ts`.
- **Not a fix for a defect.** The audit found none here. This is maintainability work and is described as such.

## Decisions

### 1. Extract by JSX region, not by concern

The six inline `//` comments already name the regions. Those become the components.

**Alternative considered — split by FRBR tier** (catalogue metadata vs. custody state vs. actions). Rejected: the tiers do not align with the visual regions, so it would require re-cutting the JSX and deciding what goes where, which is a redesign with real regression risk and no stated benefit. The comment markers are free and already correct.

### 2. One `useItemSidebarActions(item)` hook for the handler prologue

Lines 147–296 become a single hook returning the handlers, so `ItemSidebar` reads as *state + hook + six regions*.

**Alternatives considered:**
- *Pass handlers down as individual props.* Rejected: the actions region alone would take six or more props, and the same handler would be threaded through two levels to reach both actions and lending. That is the coupling the refactor exists to remove, just moved.
- *A single `sidebar` context object.* Rejected: it would make every region read `ctx.something`, hiding its real dependencies and making the components untestable in isolation. The explicitness is the point.

The hook returns a **named object**, not a positional tuple, so adding a handler does not silently reorder its consumers.

### 3. Presentational components take data, not the hook

Each region receives the values it renders plus the specific callbacks it invokes — it does not call `useItemSidebarActions()` itself.

**Reason:** two regions would otherwise each instantiate their own mutations and toasts, and a region's tests would need the hook's providers. Passing the two or three callbacks it needs keeps every region renderable from a plain object in a unit test, which is what makes the per-region tests in the proposal cheap to write.

### 4. `PrintQrCodeDialog` moves as-is

It goes into `sidebar-actions.tsx` as the static import it already is. No `dynamic()` wrapper is introduced, and none is removed.

**Reason:** the proposal's original premise here was wrong and was corrected during the audit. Adding a lazy boundary would be an unrequested behavioural change to bundle composition, and would be asserted by a test guarding a hazard that does not exist.

## Risks / Trade-offs

**[A lifted region silently renders nothing]** → The existing suites render `ItemSidebar` as a whole, so a region extracted into a component returning `null` would still pass both. Mitigation: one focused test per region asserting its distinguishing content, written in the same task as the extraction rather than afterwards — a test written later tends to assert what the code does rather than what it should.

**[Hook ordering changes]** → Moving a `useState`/`useEffect` across a component boundary changes when it runs relative to siblings. Mitigation: existing `item-sidebar.test.tsx` and `item-sidebar-media-filtering.test.tsx` already exercise the full sidebar, including the media-filtering conditional, and must pass unchanged after every extraction step. The task list sequences one region per task precisely so a regression is attributable.

**[Prop drilling returns through the orchestrator]** → `ItemSidebar` will still pass several props to each region. Mitigation: this is bounded and visible — each region's signature states its dependencies — which is strictly better than today, where they are implicit in a 540-line closure.

**[Diff size obscures review]** → A single 838-line rewrite is hard to review and, if wrong, hard to revert. Mitigation: the task list extracts **one region per task**, so each commit is small, independently reviewable, and independently revertible.

**[Over-extraction]** → Splitting further (e.g. per-badge) would produce prop-heavy fragments. Mitigation: six regions is where the comment markers are; the design deliberately stops there and says so.

## Migration Plan

None. No data migration, no API change, no feature flag. The refactor is deployed as ordinary frontend code and reverted by `git revert` of the affected commits if needed.

**Verification order per region:** extract → run `item-sidebar.test.tsx` + `item-sidebar-media-filtering.test.tsx` + `npm run type-check` → commit. Never batch two regions into one commit; that is what makes revert attributable.

## Open Questions

None that change the approach. One deferred nit is recorded rather than decided here: whether the six regions belong in a `sidebar/` subdirectory or alongside the existing flat `components/item/` files. The subdirectory is proposed because seven new files beside eleven existing ones is a meaningful difference in navigability, but it is a preference, not a constraint, and reversing it later is a mechanical move.
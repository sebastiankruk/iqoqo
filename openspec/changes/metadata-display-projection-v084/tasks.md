> **Read the design before starting.** The work is in two stages and they are independently shippable. Stage 1 removes a live rendering bug with no API change. Stage 2 is the structural change the C18 task actually asked for. **Do not begin stage 2 until stage 1's tests are green** — stage 2 moves the guarantee stage 1 establishes.
>
> **The duplication bug is real and reproduced.** `meta={{ Format: "Vinyl" }}` renders "Vinyl" twice once "Additional Details" is expanded. It is invisible in the default view because that section is collapsed, which is why it survived review.

## 0. Prove the bug before changing anything

- [ ] 0.1 Add `frontend/__tests__/components/item/extended-metadata-display.test.tsx` asserting that with `meta={{ Format: "Vinyl" }}` and the "Additional Details" section expanded, the value appears **exactly once**. **Run it against the current code and confirm it fails.** Verify: the test fails with a count of 2 before any fix. A test written only against the fixed behaviour proves nothing.
- [ ] 0.2 Extend that file to cover `Author` and `Publisher` (also absent from `hiddenKeys`), and to confirm the lowercase spellings of all three already pass. Verify: the capitalised cases fail and the lowercase cases pass on unmodified code — that asymmetry is the evidence the bug is about casing, not about rendering.

## 1. Stage 1 — derive the suppression test from the declared vocabulary

- [ ] 1.1 Export from `frontend/lib/meta.ts` a helper that answers "is this raw key a spelling of a field the page renders?", derived from `FIELD_CHAINS` rather than from a second list. **Do not add a field name to it** — that reintroduces the duplication in a new shape. Verify: the helper exists, is used by `extended-metadata.tsx`, and `FIELD_CHAINS` remains the only place a spelling is declared.
- [ ] 1.2 Replace `hiddenKeys.has(key)` in `extended-metadata.tsx` with that helper. Keep the `excludedKeys` list (`id`, `manifestation_id`, `cover_url`, `image`, `cover_status`, `cover`) as-is — those are structural column names, not metadata fields, and they are matched case-insensitively already. Verify: task 0.1's test now passes; all four cases in 0.2 pass; `extended-metadata.test.tsx` and `extended-metadata-games.test.tsx` pass unmodified.
- [ ] 1.3 Add a test asserting that **adding a spelling to `FIELD_CHAINS` alone** keeps the field rendering once — i.e. the suppression and the rendering read the same source. This is the structural guarantee, and without it the fix is only cosmetic. Verify: adding a temporary spelling to `FIELD_CHAINS` leaves the suite green (remove it afterwards).
- [ ] 1.4 Announce stage 1 in `docs/CHANGELOG.md` as a user-visible fix (a field rendering twice), referencing this change. Verify: changelog entry names the duplication and the casing cause, not the internal helper.

## 2. Stage 2 — the backend display projection

- [ ] 2.1 Create `app/core/meta_display.py` declaring, per logical field, its accepted spellings, the section it renders in, and its label. **Carry over the `label`/`publisher` precedence split explicitly** (design decision 4) — do not resolve it. Verify: the table covers every field the UI renders today, and a unit test asserts the precedence order matches what `extended-metadata.tsx` does.
- [ ] 2.2 Implement the projection builder: raw `meta` → ordered display structure, applying the value-level rules currently in the client (`unknown`, `n/a`, `none`, `""`, non-primitives dropped). Verify: unit tests cover OCR-cased input, provider-cased input, mixed input, unknown keys, and a key whose value is an object.
- [ ] 2.3 Add the projection to the item-detail response **alongside** the untouched `manifestation_meta`. Verify: the response contains both; `tests/` suites asserting on `manifestation_meta` pass unmodified; the editor path is unchanged.
- [ ] 2.4 Add the bidirectional vocabulary test between the backend table and `FIELD_CHAINS` (design decision 3). Verify: it passes, and it **fails** when a spelling is added to only one side — confirm that by adding one temporarily.
- [ ] 2.5 Add a round-trip test asserting the projection contains no field the client would have suppressed, so the two value filters cannot diverge into a doubled row. Verify: passes; and temporarily widening the client's rules makes it fail.

## 3. Adopt the projection and delete the blacklist

- [ ] 3.1 Extend `ExtendedMetadata` to accept `display` alongside `meta`, and render from it when present. **Keep the stage-1 filter as the no-projection path** (design decision 5) — the page must still render against a backend that does not send one. Verify: the stage-1 tests still pass with the prop omitted.
- [ ] 3.2 Delete `hiddenKeys` and its declaration once `display` is consumed. Verify: `grep -n "hiddenKeys" frontend/` returns nothing.
- [ ] 3.3 Update `app/item/[id]/page.tsx` to pass the projection through. Verify: `npm run type-check` clean; the component has exactly one caller, confirmed by grep rather than assumed.
- [ ] 3.4 Run the full frontend suite and the backend suite. Verify: all green; the frontend count is the pre-task count plus the new tests, with **no** previously-passing test removed or weakened.

## 4. Documentation and close-out

- [ ] 4.1 Document the projection in the API reference and note that it is additive, so consumers do not migrate away from `manifestation_meta` prematurely. Verify: the docs state both that the projection exists and that raw metadata is still authoritative.
- [ ] 4.2 Mark C18 task **3.10** complete in `openspec/changes/moderate-findings-sweep/tasks.md`, recording that MOD-FE_UI-14/19 shipped on 2026-10-01 and MOD-FE_UI-20 is delivered by this change, with the four missing spellings named. Verify: C18 increments from 30/48 to 31/48 and the entry cites this change rather than claiming the work inline.
- [ ] 4.3 Record the measured cost of deriving the projection per request, and whether caching by `meta` content hash proved necessary. If it was not, note that the deferred open question in `design.md` can now be closed. Verify: the number is written down either way, so the next reader does not re-derive it.
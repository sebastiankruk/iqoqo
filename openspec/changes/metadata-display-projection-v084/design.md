## Context

See `proposal.md` for the motivation and the reproduced duplication. What constrains the approach:

- **`hiddenKeys` is a 50-entry literal set** in `extended-metadata.tsx:130-189`, matched case-sensitively (`hiddenKeys.has(key)`) while `lib/meta.ts` establishes that one field has up to four accepted spellings. Four are currently unlisted (`Format`, `Author`, `Publisher`), verified by cross-checking the set against `FIELD_CHAINS` and confirmed by rendering the component.
- **`ExtendedMetadata`'s props are `meta`, `workMeta`, `owner_name`, `owner_count`.** The additional-details filter also applies value-level rules (`unknown`, `n/a`, `none`, `""`, non-primitives) that are genuinely display decisions, not storage decisions.
- **`manifestation_meta` is consumed by more than this component.** `item-header.tsx` and `item-sidebar.tsx` read it directly, and the item editor needs it in full. Any change must leave all of those working.
- **`lib/meta.ts` already owns the field vocabulary client-side** (`FIELD_CHAINS`), including the deliberate `label`/`publisher` precedence split — see C18 3.10's note that the two components disagree and that disagreement was preserved rather than normalised.
- **The OCR path is a real second source of casing.** `app/utils/vision.py:300-324` returns capitalised `Title`, `Subtitle`, `Authors`, `Publisher`, `Year`, `ISBN`, `Edition`, `Language`, `Genre`.

## Goals / Non-Goals

**Goals:**

- Remove the duplicate rendering, and remove the possibility of it returning when a spelling is added.
- Move the "what does this key mean and where does it render" decision to one place.
- Keep raw metadata available to the editor and to any future consumer.
- Ship the bug fix independently of the structural change, so the duplication is not held hostage to an API change.

**Non-Goals:**

- **Not a fixed schema for `meta`.** Provider payloads are open-ended; a fixed schema loses data whenever a provider adds a field.
- **Not a data migration.** Everything is derived at read time.
- **Not a change to what is stored or edited.**
- **Not a resolution of the `label`/`publisher` precedence split.** That is a product decision recorded in C18 3.10, and this change must carry it forward unchanged rather than silently pick a winner.

## Decisions

### 1. Ship the fix in two stages, with the filter fix first

**Stage 1 (no API change):** derive the suppressed-key test from `FIELD_CHAINS` — a key is suppressed if *any* accepted spelling of its logical field is on the current blacklist. This removes the duplication today and makes a future spelling addition safe, at the cost of touching one component.

**Stage 2 (API change):** the projection, after which the blacklist is deleted rather than maintained.

**Alternative — do only stage 1.** Rejected as the whole answer: it fixes the symptom while leaving the structural cause (two hand-maintained lists) in place. But it is a legitimate stopping point, and if stage 2 slips, stage 1 is a complete improvement rather than wasted work.

### 2. The projection is additive, never a replacement

`manifestation_meta` stays in the response. The item editor depends on it, third-party consumers may, and replacing it would be a breaking change for no benefit the projection does not already give.

**Alternative — replace `manifestation_meta` with the projection and keep raw behind an explicit `?raw=1`.** Rejected: it makes the common case lossy and the uncommon case deliberate, which is backwards. The editor is the uncommon case.

### 3. Derive the projection from a declared field table, and assert the two agree

The backend projection and `lib/meta.ts` both declare the same vocabulary. That is duplication, and it is the same failure mode the change exists to remove — so it is bounded explicitly:

- The backend table is the **authority**; it declares, per field, the accepted spellings, the section it renders in, and the label.
- A test asserts that **every key in `FIELD_CHAINS` appears in the backend table and vice versa.** If someone adds a spelling on one side only, the test fails and names the missing entry.
- The frontend `lib/meta.ts` is retained rather than deleted because components that read raw `meta` still need it, and the round-trip test is what keeps it honest.

**Alternative — a single generated JSON artefact consumed by both.** Rejected as over-engineering for ten fields, and it introduces a codegen step and a staleness question that is worse than the duplication it removes.

### 4. Preserve the `label`/`publisher` precedence split explicitly

The projection declares the label/publisher pair as two fields sharing a section with an explicit precedence order, rather than collapsing them. `ExtendedMetadata` currently prefers `label` under a "Label / Publisher" heading while `ItemHeader` prefers `publisher`; that disagreement is deliberate and documented, and the projection must encode both rather than resolving it.

### 5. Value-level display rules move to the server; the client keeps a fallback

The `unknown` / `n/a` / `none` / `""` / non-primitive filtering is a display decision, so it belongs in the projection. The client keeps an equivalent filter for the no-projection path, because an older server may not send one and the page must still render.

**Rejected — drop the client filter and require the projection.** That makes the page blank against any server that does not send it, including a rolled-back backend. The duplication of the rule is smaller than the failure mode.

## Risks / Trade-offs

**[The backend/frontend vocabulary tables drift]** → The bidirectional test from decision 3. A drift fails the build naming both the missing key and the file, rather than duplicating a field on a collapsed panel.

**[A projection is derived per request and costs time on the item detail path]** → Measure before optimising. The derivation is a pass over `meta`'s keys with set lookups; if it shows up, cache by `meta`'s content hash, which is stable for a given record. Do not precompute into a column, since that reintroduces the staleness problem the additive design avoids.

**[`ExtendedMetadata` prop change breaks a caller]** → It has exactly one caller (`app/item/[id]/page.tsx`); verified, not assumed. A type change surfaces any others at compile time.

**[The client and server value filters disagree]** → They start from the same rule list. The round-trip test asserts the projection never contains a field the client would have suppressed, so divergence fails a test rather than producing a doubled row.

**[Over-scoping into a `meta` schema]** → Explicitly a non-goal, and the additive projection is what makes it unnecessary.

## Migration Plan

None. No schema change, no backfill, no dual-write.

**Rollback:** stage 2 is revertible by reverting the endpoint change; the additive projection means a client still renders correctly against a backend that stops sending it.

**Sequencing:** stage 1 may ship on its own. Stage 2 requires the round-trip tests from stage 1 to be green first, so the duplicate-rendering guarantee is established before the structural change moves it.

## Open Questions

None that change the approach. Two deferred items, recorded rather than decided:

- Whether the backend table should live in `app/core/meta_display.py` or alongside the existing normalisation helpers in `app/core/format_normalizer.py`. The former is proposed because this is a distinct concern from format *string* normalisation, and the existing file's name would be misleading if it grew to cover field display.
- Whether the projection is computed server-side per request or pushed to the client at hydration. Deferred until measurement, per the risk note above.
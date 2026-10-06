## Why

C18 task **3.10** (MOD-FE_UI-20) asks to *"replace hiddenKeys blacklist in `extended-metadata.tsx` with backend-provided metadata separation."* Two of three parts of 3.10 shipped on 2026-10-01 (`frontend/lib/meta.ts` and the converted fallback chains). This change is the third, deferred because it needs a schema decision rather than a client-side patch.

**Auditing it produced a reproducible rendering bug today, which this change fixes.**

`ExtendedMetadata` keeps a 50-entry `hiddenKeys` set listing every metadata key it renders in a dedicated section, so those keys can be omitted from the catch-all "Additional Details" block. The set is matched **case-sensitively** against the raw key, while `lib/meta.ts` (C18 3.10) established that the same logical field legitimately arrives under several spellings — the OCR path in `app/utils/vision.py:300-324` returns `Title`, `Authors`, `Publisher`, `Year` and `ISBN` all capitalised, while the provider adapters write lowercase.

Four accepted spellings are missing from the blacklist, so a record produced by OCR renders the same field twice:

```
Media Format
Vinyl                      <- dedicated section

Additional Details
Format   Vinyl             <- the same value again
```

Verified by rendering the component with `meta={{ Format: "Vinyl" }}` and expanding the details block: `Vinyl` appears **twice**. The duplication is easy to miss because "Additional Details" is collapsed behind a toggle by default, so the default view looks correct.

The missing spellings, cross-checked against `FIELD_CHAINS` in `lib/meta.ts`:

| Field | Accepted spellings | Absent from `hiddenKeys` |
|---|---|---|
| `format` | `format`, `Format` | **`Format`** |
| `author` / `authors` | `author`, `authors`, `Author`, `Authors` | **`Author`** |
| `publisher` | `publisher`, `label`, `Publisher` | **`Publisher`** |

**The structural problem is that the blacklist must be maintained by hand in step with `FIELD_CHAINS`.** Two lists describing the same field vocabulary, with no link between them, and the only signal of drift is a duplicated row on a collapsed panel. A fourth accepted spelling would reintroduce it.

## What Changes

- **Immediate:** make the "Additional Details" filter reject a key when *any* spelling of the same logical field is on the blacklist. The filter gains access to `FIELD_CHAINS` rather than its own hand-maintained copy, so the two can no longer disagree. This is a small, self-contained fix that removes the bug without any API change.
- **Structural:** the API stops shipping raw provider metadata to the item-detail page. `GET /api/v1/items/<id>` gains a **display projection** of `manifestation_meta`: a server-derived, per-field structure carrying only what the UI renders, with the display decision made once on the server instead of re-inferred in the browser.
- The projection is **additive**. `manifestation_meta` continues to be returned in full, so no existing consumer breaks and the item editor — which genuinely needs raw metadata to edit it — keeps working.
- The `hiddenKeys` blacklist is **deleted** once the projection exists. It is the third and last place that field vocabulary is hand-maintained.
- The projection is computed from the same `FIELD_CHAINS`-equivalent mapping on the backend, and is therefore correct by construction for OCR-sourced and provider-sourced records alike.
- **BREAKING for the item-detail page only**, once the projection is adopted: `ExtendedMetadata` stops consulting `hiddenKeys` and reads the projection. The component's props change to accept `display` alongside `meta`, which is why this is a real requirement change rather than an internal refactor.

### Explicitly not in scope

- **No change to what is stored.** `meta` stays a free-form JSONB column, because provider payloads are genuinely open-ended and a fixed schema would lose data on every new provider field.
- **No change to the item editor.** It edits raw metadata and must keep full access.
- **No backfill and no migration.** The projection is derived at read time from data already present.

## Capabilities

### New Capabilities

- `metadata-display-projection`: How provider metadata is turned into the ordered, de-duplicated field set the item detail page renders, why that decision belongs on the server, and the guarantee that a field renders exactly once regardless of which spelling its source used.

### Modified Capabilities

- `frontend`: The item detail page renders its metadata sections from the server's display projection rather than from a client-side key blacklist, and `ExtendedMetadata`'s props change accordingly.

## Impact

**Backend**

- New projection builder — `app/core/meta_display.py` — mapping raw `meta` to an ordered display structure, plus the item-detail endpoint change.
- The field-vocabulary mapping now exists **twice in the repository** (backend projection and `frontend/lib/meta.ts`) rather than twice client-side. That is a real cost, and it is the same kind the change is trying to eliminate — see `design.md`, which argues the backend copy should be the single source and the frontend consume the projection rather than keep its own map.

**Frontend**

- `frontend/components/item/extended-metadata.tsx` — `hiddenKeys` deleted, props extended.
- `frontend/lib/meta.ts` — unchanged; it remains correct for the components that still read raw `meta` (the item header, the sidebar).

**Tests**

- New: a rendering test per spelling, asserting the field appears exactly once. Written against the current code first, so the duplication is demonstrated before it is fixed.
- New: projection unit tests covering OCR-cased input, provider-cased input, mixed input, and unknown keys.
- Existing `extended-metadata.test.tsx` and `extended-metadata-games.test.tsx` must pass through both stages.

**Risks** — the projection could drift from what the UI actually renders if the two are developed separately. `design.md` addresses this by deriving the display order from one shared declaration and asserting the round-trip.

**Scheduling** — v0.8.4. This was split out of C18 precisely because the schema/API decision does not belong in a moderate-findings sweep, and because the immediate fix (the case-insensitive filter) can ship independently of the projection.
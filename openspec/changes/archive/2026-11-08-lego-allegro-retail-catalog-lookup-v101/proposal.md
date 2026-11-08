# Proposal: LEGO Allegro Retail Catalog & Barcode Lookup Fallback

## Problem

In release `1.0.1`, LEGO sets can be looked up via Rebrickable (`C104`). However, many European collectors scan standard EAN-13 barcodes (`570201...`) from physical boxes purchased in Poland and Europe. If `REBRICKABLE_API_KEY` is not configured, or if a barcode is not indexed directly in Rebrickable, or if quick-lookup is used with the LEGO icon selected, several gaps appeared:

1. `LegoLookupStrategy` only called `fetch_rebrickable_set()` and `search_rebrickable_sets()`. When it called `resolve_physical_media(barcode)`, it extracted the set number and queried Rebrickable again; if Rebrickable failed, it discarded any Allegro metadata.
2. `app/api/scanner.py` only invoked `fetch_allegro_candidates()` when `category_hint in ("text", "book")`, omitting Allegro for LEGO candidate searches (`category_hint == "lego"`).
3. In `frontend/app/scan/page.tsx`, `formatToApiParam()` omitted a branch for `"lego"`, dropping `?format=lego` during quick-lookup by barcode/number, while `_normalize_preview_meta()` in `app/api/scanner.py` lacked `"lego"` in `hint_to_format`, causing Allegro-resolved LEGO sets to be saved with `format="book"` and `Expression.content_type="text"`.

## Solution

1. **Extend `LegoLookupStrategy` in `app/strategies/lego.py` & `app/utils/allegro.py`**:
   - When an EAN/UPC barcode is scanned and Rebrickable set lookup does not return metadata (or Rebrickable is unconfigured), invoke `fetch_allegro_metadata(cleaned_barcode)` as a first-class retail fallback provider (`data_source="allegro"`, `provider="allegro"`, `format="standard_set"`, `category="lego"`).
   - Extract `set_number` (via `Numer produktu`, `Numer zestawu`, `Kod producenta` parameters or title regex `\b(\d{4,6})\b`), `piece_count` (`Liczba elementów`, `Liczba klocków`), `theme` (`Seria`, `Linia`), Polish title, and high-resolution cover image from Allegro product/offer metadata.
   - If Rebrickable is available, enrich the Allegro result with Rebrickable piece count/minifigs/theme if missing; otherwise return the normalized LEGO manifestation dictionary.
2. **Support LEGO in Candidate Search**:
   - In `LegoLookupStrategy.lookup_candidates()`, query `fetch_allegro_candidates(query)` if Rebrickable results are fewer than `max_results` or if Rebrickable fails.
   - In `app/api/scanner.py`, route `category_hint == "lego"` candidate searches through `LegoLookupStrategy().lookup_candidates()`.
3. **Preserve LEGO Format Hint in Scanner Quick-Lookup & Backend Normalization**:
   - Update `formatToApiParam()` in `frontend/app/scan/page.tsx` to return `"lego"` when `fmt === "lego"`.
   - Update `_normalize_preview_meta()` in `app/api/scanner.py` to map `"lego"` and `"construction_set"` in `hint_to_format` to `MediaFormat.STANDARD_SET` (`"standard_set"`).
4. **Tests & Ontological Consistency**:
   - Add unit and API tests verifying barcode resolution, Allegro parameter extraction, candidate search, and scanner format normalization for LEGO sets.
   - Maintain FRBRoo ontological integrity (`F16_Container_Work`, `F3_Manifestation_Product_Type`, `MediaCategory.LEGO`).

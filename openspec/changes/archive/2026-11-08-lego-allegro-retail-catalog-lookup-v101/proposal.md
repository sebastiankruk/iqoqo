# Proposal: LEGO Allegro Retail Catalog & Barcode Lookup Fallback

## Problem
In release `1.0.1`, LEGO sets can be looked up via Rebrickable (`C104`). However, many European collectors scan standard EAN-13 barcodes (`570201...`) from physical boxes purchased in Poland and Europe. If `REBRICKABLE_API_KEY` is not configured, or if a barcode is not indexed directly in Rebrickable, or if title searches are performed for LEGO sets, the system fails to resolve metadata because:
1. `LegoLookupStrategy` only calls `fetch_rebrickable_set()` and `search_rebrickable_sets()`. When it calls `resolve_physical_media(barcode)`, it extracts the set number and queries Rebrickable again; if Rebrickable fails, it discards any Allegro metadata!
2. `app/api/scanner.py` only invokes `fetch_allegro_candidates()` when `category_hint in ("text", "book")`, completely omitting Allegro for LEGO searches (`category_hint == "lego"`).

## Solution
1. **Extend `LegoLookupStrategy` in `app/strategies/lego.py`**:
   - When an EAN/UPC barcode is scanned and Rebrickable set lookup does not return metadata (or Rebrickable is unconfigured), invoke `fetch_allegro_metadata(cleaned_barcode)` as a first-class retail fallback provider (`data_source="allegro"`, `provider="allegro"`).
   - Extract `set_number` (via parameter or title regex `\b(\d{4,6})\b`), `piece_count`, `theme`, Polish title, and high-resolution cover image from Allegro product/offer metadata.
   - If Rebrickable is available, enrich the Allegro result with Rebrickable piece count/theme if missing; otherwise return normalized LEGO manifestation dictionary.
2. **Support LEGO in Candidate Search**:
   - In `LegoLookupStrategy.lookup_candidates()`, query `fetch_allegro_candidates(query)` if Rebrickable results are fewer than `max_results` or if Rebrickable fails.
   - In `app/api/scanner.py`, include `fetch_allegro_candidates(query)` for `category_hint == "lego"` or `format_hint == "lego"`.
3. **Tests & Ontological Consistency**:
   - Add unit tests verifying barcode resolution and candidate search for LEGO sets via Allegro fallback.
   - Maintain FRBRoo ontological integrity (`F16_Container_Work`, `F3_Manifestation_Product_Type`).

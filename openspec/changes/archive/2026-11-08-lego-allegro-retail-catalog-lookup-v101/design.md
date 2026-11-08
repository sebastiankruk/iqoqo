# Design: LEGO Allegro Retail Catalog & Barcode Lookup Fallback

## Architecture Overview
The LEGO metadata resolution pipeline (`LegoLookupStrategy`) follows a waterfall architecture:
1. Direct LEGO Set Number lookup (`10318` -> Rebrickable).
2. Physical EAN/UPC Barcode resolution:
   - Try Rebrickable barcode search.
   - If Rebrickable does not resolve or returns no hit, try `fetch_allegro_metadata(cleaned_barcode)`.
   - If Allegro returns product/offer data:
     - Extract `set_number` from Allegro parameters (`Numer produktu`, `Kod producenta`) or title regex (`\b(\d{4,6})\b`).
     - Extract `piece_count` from Allegro parameters (`Liczba elementów`).
     - Extract `theme` / `series` from Allegro parameters (`Seria`).
     - If `set_number` is found and Rebrickable is configured, attempt secondary enrichment of minifig count or theme name.
     - Return normalized dictionary with `data_source="allegro"` and provider `"allegro"`.
   - If Allegro fails, fall back to UPC database waterfall (`resolve_physical_media`).
3. Free-text Candidate Search:
   - In `LegoLookupStrategy.lookup_candidates(query, max_results)`:
     - Call `search_rebrickable_sets(query, max_results)`.
     - If candidate count < `max_results`, call `fetch_allegro_candidates(query, max_results - len(candidates))`.
     - Merge candidates and return.
   - In `app/api/scanner.py`:
     - Allow `category_hint == "lego"` or `format_hint == "lego"` to query `fetch_allegro_candidates(query)` alongside Rebrickable.

## Data Structures
Normalized Allegro LEGO dictionary returned by `LegoLookupStrategy.lookup()`:
```python
{
    "title": "LEGO Icons 10318 Concorde",
    "barcode": "5702018068229",
    "set_number": "10318",
    "piece_count": 2083,
    "theme": "LEGO Icons",
    "cover_url": "https://a.allegroimg.com/...",
    "source": "allegro",
    "data_source": "allegro",
    "format": "construction_set",
    "category": "lego",
}
```

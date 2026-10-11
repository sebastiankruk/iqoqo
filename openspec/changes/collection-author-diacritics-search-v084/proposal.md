## Why

When users search or filter collections (e.g. `https://iqoqo.cc/collection?q=Gabriel+García+Márquez`), searching by author or creator name fails because the collection query only searches Work titles and ISBNs. In addition, search requires exact diacritical characters (e.g. typing `milosc` fails to match `miłość`), preventing users from finding cataloged works when using standard ASCII keyboards or mobile devices without diacritical character pickers. Addressing this in `v0.8.4` resolves dev-note items `#bugs #v084` ("filtering by authors with special characters in names does not work" and "filtering requires to give exact special characters, e.g., miłość is ok - milosc - does not work").

## What Changes

- **Author and Contributor Query Matching:** Extend `SearchService.search_items` to search Work and Expression contributors (`Agent` / `WorkContribution` / `ExpressionContribution`) as well as Manifestation author metadata alongside Work titles and ISBNs.
- **Diacritic-Insensitive Search (Unaccent):** Enable PostgreSQL `unaccent` dictionary extension and apply diacritic folding to full-text search queries and fallback ILIKE comparisons, allowing unaccented queries (`milosc`, `Garcia`) to match accented database entities (`miłość`, `García`) and vice versa.
- **Query Parsing Resilience:** Ensure queries containing multi-word author names with diacritics and special characters are parsed cleanly without breaking `websearch_to_tsquery` or triggering SQL errors.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `search-special-character-handling`: Add requirements for diacritic-insensitive search normalization (unaccent) and contributor name matching in collection queries.

## Impact

- **Backend:** `app/core/search_service.py` (`_pg_item_fts` and `_ilike_item_search`), `app/db/` migration enabling `unaccent` PostgreSQL extension.
- **Specs:** `openspec/specs/search-special-character-handling/spec.md`.
- **Tests:** `tests/test_search.py` unit and integration tests covering author names with special characters and diacritic-agnostic searches.

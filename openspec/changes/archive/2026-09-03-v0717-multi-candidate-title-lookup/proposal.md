## Why
Popular titles (e.g., "Jaś i Małgosia") return only a single result when queried, instead of a list of candidates for disambiguation. This prevents users from selecting the correct edition when searching by title.

## What Changes
- Refactor title lookup providers to accept `max_results` (default 10).
- Aggregate candidates and return them as an array.
- Update scanner API to package multi-candidate responses.

## Capabilities

### New Capabilities

### Modified Capabilities

## Impact
- `app/strategies/book.py`
- `app/utils/allegro.py`
- `app/utils/isbn.py`
- `app/api/scanner.py`

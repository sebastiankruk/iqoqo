## Why

Book scanning can return "found" with unknown title/author when Google Books intermittently fails with 429/5xx responses. The current provider chain aborts before Open Library and downstream sources can answer, so a known ISBN can appear empty during a 0.7.14 preview acceptance scan.

## What Changes

- Make external book lookup failure-aware: distinguish definitive no-result from transient provider failure.
- Retry Google Books once only after a transient Google failure, after attempting Open Library.
- Continue fallback from Google Books to Open Library, then Allegro and other existing book providers.
- Keep lookup latency bounded by allowing only one Google retry and short backoff.
- Preserve provider provenance and scanner telemetry for each external lookup outcome.
- Add regression coverage for Google Books 429/503, Open Library fallback, one-shot Google retry, and downstream provider continuation.

## Capabilities

### New Capabilities

- `book-provider-fallback-retry`: Resilient book metadata lookup with failure-aware provider fallback and a bounded Google Books retry.

### Modified Capabilities

- None.

## Impact

- `app/utils/isbn.py`: provider outcome handling and bounded retry behavior.
- `app/strategies/book.py`: provider-chain continuation after transient Google failures.
- `app/api/scanner.py`: preserves the successful external metadata path and telemetry semantics.
- Backend tests for ISBN lookup and scanner preview behavior.
- 0.7.14 release acceptance for book scanning.

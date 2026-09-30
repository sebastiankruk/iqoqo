## 1. Provider outcome model

- [x] 1.1 Add an internal ISBN provider outcome representation that distinguishes success, definitive no-result, and transient failure.
- [x] 1.2 Map Google Books HTTP 429/5xx and request-level network failures to transient failure without logging API keys or credential-bearing URLs.
- [x] 1.3 Map successful Google Books responses with zero items and Open Library responses with no metadata to definitive no-result.

## 2. Resilient lookup chain

- [x] 2.1 Update `app/utils/isbn.py` so transient Google Books failure immediately attempts Open Library.
- [x] 2.2 Retry Google Books exactly once only when the first Google response was transient and Open Library returned no metadata.
- [x] 2.3 Apply a short fixed delay suitable for interactive scanning and prevent more than one Google retry per lookup.
- [x] 2.4 Return successful metadata with the actual provider source and preserve existing normalization keys.
- [x] 2.5 Ensure `app/strategies/book.py` continues to Allegro and downstream providers when ISBN provider outcomes are exhausted.

## 3. Regression tests

- [x] 3.1 Add a backend test where Google Books returns 429/503 and Open Library returns `The Rough Guide to the USA` metadata.
- [x] 3.2 Add a backend test where Google Books returns a successful empty result and verify Google is not retried.
- [x] 3.3 Add a backend test where Google first fails transiently, Open Library has no result, and the single Google retry succeeds.
- [x] 3.4 Add a backend test where both Google attempts fail transiently and the existing downstream provider chain continues.
- [x] 3.5 Add a scanner preview regression test proving title and author are returned after Open Library fallback.

## 4. Validation and release readiness

- [x] 4.1 Run focused backend tests for ISBN lookup and scanner preview behavior.
- [x] 4.2 Run `make test` and the relevant scanner/frontend test suites.
- [x] 4.3 Validate preview with ISBN `9781843537861` and simulated Google 429/503 behavior.
- [x] 4.4 Confirm logs and telemetry contain provider outcome and ISBN but no Google API key or credential-bearing URL.
- [x] 4.5 Update the 0.7.14 pre-release acceptance runbook if the scanner verification wording needs the fallback behavior explicitly noted.

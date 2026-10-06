## Context

The book scanner currently treats Google Books as the first metadata provider and Open Library as the fallback. During the 0.7.14 preview acceptance test, Google Books intermittently returned transient failures for a valid ISBN. The exception prevented the fallback chain from continuing, leaving the scanner with a successful-looking but empty metadata result.

The change must be small enough for 0.7.14 and must not broaden provider behavior beyond resilient fallback. Preview should remain operational even when Google Books is rate-limited or temporarily unavailable.

## Goals / Non-Goals

**Goals:**

- Preserve Google Books as the preferred book provider.
- Continue to Open Library when Google Books returns 429/5xx or a request-level transient failure.
- Retry Google Books once only when its first failure was transient and Open Library returned no metadata.
- Continue to Allegro and existing downstream providers after both Google attempts and Open Library are exhausted.
- Keep total scan latency bounded and avoid repeated provider polling.
- Record enough telemetry to distinguish provider success, definitive no-result, and transient failure.

**Non-Goals:**

- Do not add a new bibliographic provider.
- Do not change scanner UI copy or FRBR modeling.
- Do not introduce background queueing or infinite retry loops.
- Do not retry Google Books after a definitive Google no-result.
- Do not change successful CD, vinyl, or other non-book lookup paths.

## Decisions

1. **Represent provider outcomes as statuses**

   Introduce a small internal result structure that distinguishes `success`, `no_result`, and `transient_failure`. This avoids using exceptions as control flow across the provider chain.

   Alternative considered: continue returning only metadata or `None`. Rejected because `None` cannot distinguish "not found" from "provider unavailable," which determines whether the one-shot Google retry is allowed.

2. **Keep retry ownership inside ISBN lookup utilities**

   `app/utils/isbn.py` owns Google Books/Open Library sequencing and the one-shot Google retry. `app/strategies/book.py` continues to Allegro and other downstream providers when ISBN lookup returns no metadata.

   Alternative considered: put all fallback logic in `BookLookupStrategy`. Rejected because Google/Open Library are already encapsulated in `fetch_isbn_metadata()` and are reused by manifestation APIs and ingest paths.

3. **Allow exactly one Google retry after Open Library no-result**

   If Google attempt A is transient and Open Library succeeds, return Open Library immediately. If Open Library has no result, retry Google once with a short bounded backoff. If Google attempt B fails or has no result, continue to Allegro and downstream providers.

   Alternative considered: retry Google immediately. Rejected because Open Library provides faster recovery and avoids amplifying a Google outage.

4. **Short bounded delay only**

   Use a short fixed delay suitable for an interactive scan, approximately 1 second, and do not retry more than once.

   Alternative considered: exponential backoff. Rejected because a barcode scan is synchronous and must remain responsive.

5. **Preserve provider provenance**

   The returned metadata must retain its actual source (`google_books` or `open_library`). Scanner telemetry should continue reporting the successful external provider rather than claiming Google success after a fallback.

6. **Log failures without secrets**

   Logs may include provider, ISBN, HTTP status, and attempt class. They must not include the Google API key, request URLs containing query parameters with credentials, or OAuth tokens.

## Risks / Trade-offs

- [Extra request latency during Google outages] → Only one retry and a short fixed delay; Open Library usually resolves valid ISBNs before the retry.
- [Google quota pressure from a retry] → Retry only after transient Google failure and Open Library no-result; never retry definitive no-results.
- [Provider disagreement between Google and Open Library] → Preserve first successful provider result and provenance; do not merge conflicting titles/authors.
- [Allegro token expired] → Treat Allegro as unavailable and continue through the existing provider chain without repeated authorization attempts.

## Migration Plan

- Add focused backend unit tests around ISBN provider outcomes and scanner book lookup.
- Deploy as part of 0.7.14; no schema migration is required.
- Validate on preview using ISBN `9781843537861` while simulating Google 429/503 and Open Library success.
- Roll back by reverting the lookup utility change; no data or environment rollback is required.

## Open Questions

- Whether scanner telemetry should expose each provider attempt to administrators now or remain summarized at the successful provider level for 0.7.14.

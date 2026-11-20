## Context

See `proposal.md` and `.context/notes/review/1.1.0/principal-review-release-1.1.0.md`. All nine items are low-severity polish and query-hygiene improvements intentionally deferred to `v1.1.1` so `v1.1.0` stays surgical.

## Goals / Non-Goals

**Goals:**
- Eliminate redundant DB queries, non-deterministic tie-breaks, legacy SA 1.x `.query` remnants, and minor RDF/serial/UI rough edges.
- Maintain full backward compatibility with `v1.1.0` schemas and APIs (zero migrations required).

**Non-Goals:**
- Critical/moderate `v1.1.0` blockers (tracked in `C136` `v110-review-remediation-and-hardening`).
- Breaking API or UI redesigns.

## Decisions

1. **Single-pass share lookup & SSR cache respect:**
   - Add an internal helper returning `(items, is_private_cache)` so `public_items.py` and `public_rdf.py` query `SharedCollection` and `is_friend_of()` once per request.
   - In `frontend/lib/share-server.tsx`, avoid `{ next: { revalidate: 60 } }` on responses that cannot be publicly cached (or default to `cache: "no-store"` unless public cacheability is guaranteed).
2. **Deterministic rollup & SA 2.0 `works.py`:**
   - Add an explicit `ORDER BY` / deterministic status precedence tuple in `compute_work_reading_rollup()` and ignore `rank == 0` entries.
   - Replace `db.session.query(Item.id)` in `app/api/works.py` with `select(Item.id)`.
3. **Serial RDF, dedupe & telemetry:**
   - Include `"publication_year"` in `build_collection_rdf_graph`'s serial key tuple and wrap `int(...)` casts in `_safe_int()`.
   - Change `Expression.work_id == work.id` to `Manifestation.expression_id == expression.id` in `ingest_serial_from_meta()` issue dedupe.
   - Expand EAN-2 add-on upper bound from `12` to `53` in `app/utils/issn.py`.
   - Wrap BN/Crossref/OpenLibrary requests in `app/strategies/serials.py` with `record_outbound_telemetry`.
4. **Vision & `/collection` polish:**
   - Pass resolved `serial_title` into `_pick_serial_headline()` instead of hardcoding `"national geographic"`.
   - Compute `vision_ready` in `get_llm_vision_status(probe_ollama=False)` using configured Ollama URL + vision model when probing is skipped.
   - Use `func.count(func.distinct(Item.id))` for `total_physical` in `app/api/items.py`.
   - Reset `selectedItemIds` via `useEffect` on filter/query/scope/viewMode changes in `frontend/app/collection/page.tsx` and add outside-click + `Escape` handlers in `BulkItemVisibilityToolbar`.

## Risks / Trade-offs

- **Expression-scoped serial dedupe** → Keep fallback matching clean so single-expression serials still deduplicate identically while multi-language editions stay isolated.
- **Disabling 60s SSR ISR cache on share links** → Slight increase in backend SSR hits for anonymous share views, mitigated by Flask's `Cache-Control: public, max-age=300` + `Vary: Authorization, Cookie` at Nginx/Cloudflare.

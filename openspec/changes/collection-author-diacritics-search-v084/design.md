## Context

Collection searching (`/collection?q=...`) in `app/core/search_service.py` currently handles search via `_pg_item_fts` (PostgreSQL full-text search using `websearch_to_tsquery('simple', :q)`) or fallback `_ilike_item_search`.
Two critical gaps exist:
1. `_ilike_item_search` only inspects `Work.title` and `Manifestation.isbn13`. It does not join `WorkContribution`, `ExpressionContribution`, or `Agent`, meaning author searches (such as "Gabriel García Márquez") fail completely.
2. Search vectors use the PostgreSQL `simple` text search configuration without diacritical folding (`unaccent`). As a result, searching for `milosc` fails to match `miłość`, and searching for `Garcia` fails to match `García`.

See `proposal.md` for user problem and dev-note references.

## Goals / Non-Goals

**Goals:**
- Include contributor and author names (`Agent.name` linked via Work and Expression contributions, as well as Manifestation author arrays) in both PostgreSQL FTS and fallback ILIKE item search queries.
- Enable diacritic-agnostic query resolution in PostgreSQL via `unaccent` extension, and provide SQLite-compatible Python-level normalization in tests.
- Maintain compatibility with all existing search facets (tags, collections, publishers, statuses).

**Non-Goals:**
- Phonetic search (e.g. Soundex / Metaphone) or Levenshtein fuzzy typo correction (deferred to future search enhancements).
- External search engine dependencies (e.g. Elasticsearch or MeiliSearch).

## Decisions

### Decision 1: PostgreSQL `unaccent` Extension & FTS Search Vectors
- **Approach:** Add Alembic migration ensuring `CREATE EXTENSION IF NOT EXISTS unaccent;`. Update `websearch_to_tsquery` to evaluate against unaccented tokens: `websearch_to_tsquery('simple', immutable_unaccent(:q))` matching `to_tsvector('simple', immutable_unaccent(coalesce(w.title, '')))`.
- **Rationale:** Native Postgres indexing maintains sub-millisecond search performance for catalogs with thousands of items.
- **Alternatives Considered:** Python-only query expansion generating permutations. Rejected due to combinatorial explosion and severe performance degradation on multi-word names.

### Decision 2: Contributor Search Association in `search_items`
- **Approach:** Join `WorkContribution` and `Agent` on `Work.id` in `_ilike_item_search` and include `Agent.name` in FTS document weighting.
- **Rationale:** Allows users searching "Gabriel García Márquez" or "Stanisław Lem" in the collection view to instantly retrieve all corresponding items.

### Decision 3: SQLite Dialect Compatibility for Testing
- **Approach:** In SQLite (used by in-memory unit tests), detect dialect and apply Python `unicodedata.normalize('NFKD', ...)` diacritic folding and ILIKE fallback.
- **Rationale:** Ensures pytest test suite runs cleanly and fast in local and CI environments without forcing Postgres container startup for quick unit tests.

## Risks / Trade-offs

- **[Risk]** `unaccent()` in PostgreSQL is not immutable by default, preventing its direct use in generated/indexed column expressions.
  → *Mitigation:* Create a small `immutable_unaccent(text)` wrapper function in the database migration, a standard PostgreSQL best practice.
- **[Risk]** Query latency overhead from joining `Agent` table in ILIKE queries.
  → *Mitigation:* Apply index on `Agent.name` and use `db.session.query(Manifestation.id).join(...)` with distinct/grouping.

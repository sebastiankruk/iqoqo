## Context

`GET /api/manifestations/<id>/images` (`app/api/manifestations.py:1047`) already returns additional `ImageScan` records attached to a `Manifestation` (`F3`), and `Item` / `ReadingTransition` / `reading_sessions` already store personal reading telemetry (`C115`). However, `/manifestation/[id]` (`ManifestationDetailClient`) does not display contributed covers or anonymized reading/popularity analytics.

## Goals / Non-Goals

- **Goals:**
  - Surface a contributed covers & edition scans gallery on `/manifestation/[id]` using `GET /api/manifestations/<id>/images` with lightbox preview and `F3` source/label badges (without exposing uploader user IDs).
  - Add `GET /api/manifestations/<id>/stats` returning anonymized, visibility-safe `GROUP BY` aggregates: reader count, completed count, average reading duration (days/minutes), and monthly popularity-over-time buckets (`added_count`, `completed_count`).
  - Render a clean Read Stats & Popularity Over Time card on `/manifestation/[id]` with graceful empty states.
- **Non-Goals:**
  - Exposing individual reader profiles, private `Item` records, or `reading_sessions.notes`.
  - Executing per-month or per-item Python loops (N+1 queries); all analytics MUST use SQL `GROUP BY` aggregates.

## Decisions

- **Anonymized `GROUP BY` Aggregation:**
  - `GET /api/manifestations/<id>/stats` computes counts via `func.count(...)` (`# pylint: disable=not-callable`) grouped by status and `date_trunc('month', ...)` (PostgreSQL) / `strftime('%Y-%m', ...)` (SQLite test fallback) across `Item`s linked to `manifestation_id` where `Item.visibility != 'private'` (or all owned if no PII is returned; specifically aggregate counts only when `>= 1` non-private item or owner-inclusive aggregate without any user identifiers).
  - Zero user IDs, item IDs, or session notes are ever included in the response payload.
- **Frontend Gallery & Chart:**
  - `ManifestationCoversGallery` fetches `GET /api/manifestations/<id>/images`, deduplicating against the primary `cover_url`.
  - `ManifestationStatsCard` renders KPI pills + a lightweight responsive SVG/Tailwind bar/area timeline (no heavy charting bundle bloat).

## Risks / Trade-offs

- **SQLite vs PostgreSQL date-truncation:** Backend tests run on SQLite while production runs PostgreSQL; use a dialect-aware helper (`_month_bucket_expr(dialect, col)`) tested on both dialects.

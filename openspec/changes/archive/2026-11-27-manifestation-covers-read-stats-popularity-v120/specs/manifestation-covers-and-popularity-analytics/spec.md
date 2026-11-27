## ADDED Requirements

### Requirement: Manifestation Contributed Covers Gallery
The `/manifestation/[id]` detail view MUST display community-contributed edition covers and supplementary scans (`ImageScan`) attached to the `Manifestation` (`F3`) without leaking uploader identities.

#### Scenario: Rendering contributed covers on manifestation detail
- **WHEN** a user views `/manifestation/[id]` for a manifestation that has `ImageScan` records returned by `GET /api/manifestations/<id>/images`
- **THEN** `ManifestationCoversGallery` renders thumbnails with `label` and `source` provenance badges and supports full-size preview, omitting any private uploader user IDs

### Requirement: Anonymized Manifestation Read Stats & Popularity Over Time
The backend MUST expose anonymized `GROUP BY` reading statistics and popularity-over-time buckets for a `Manifestation` without N+1 queries or PII leakage.

#### Scenario: Fetching manifestation stats and monthly popularity
- **WHEN** a client requests `GET /api/manifestations/<id>/stats`
- **THEN** the endpoint returns `total_items`, `reader_count`, `completed_count`, `avg_reading_days`, `avg_session_minutes`, and `popularity_over_time` (`[{ month, added_count, completed_count }]`) computed via SQL `GROUP BY` aggregates, containing zero user IDs or session notes

#### Scenario: Graceful empty state for un-read manifestations
- **WHEN** a manifestation has zero reading sessions or transitions
- **THEN** `GET /api/manifestations/<id>/stats` returns `200` with zeroed counts / `null` averages and `/manifestation/[id]` renders a non-error empty state

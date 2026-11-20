## Context

See `proposal.md` for motivation and physical *National Geographic Polska* evidence. Previously `shared/taxonomy.yaml` only listed `magazine` as a `MediaFormat` under `text`, without `Work.issn`, issue-level columns on `Manifestation`, or `F18_Serial_Work` RDF modeling.

## Goals / Non-Goals

**Goals:**
- Establish clean FRBRoo `F18_Serial_Work` (serial title + ISSN) vs `Manifestation` (individual issue + `977` EAN + 2-digit add-on) modeling.
- Support both standalone ISSN periodicals (*National Geographic Polska* `1507-5966`) and bilingual/multi-language editions (*National Geographic* US `0027-9358` vs *Polska* `1507-5966` — note each has its own ISSN!).
- Keep `Manifestation.ean` non-unique so multiple issues within a year/price variant can share `9771507596044` while being disambiguated via `full_barcode` (`977150759604407`) or `(issue_number, publication_year)`.

**Non-Goals:**
- Indexing individual magazine articles as separate sub-Works (article-level decomposition can build on `WorkPart` later if ever desired).
- Implementing external ISSN/scanner HTTP strategies (covered by `C132: journals-issn-lookup-scanner-and-issue-ui-v110`).

## Decisions

1. **Dedicated relational columns on `Work` (`issn`, `eissn`, `work_kind`) and `Manifestation` (`issue_number`, `cumulative_issue_number`, `volume`, `publication_year`, `publication_month`, `ean_addon`, `full_barcode`):** Indexed columns allow fast O(log N) lookup by ISSN (`1507-5966`) or 15-digit `full_barcode` (`977150759604407`) without full-table JSON scans, while `cover_headline` and `indeks` (`323357`) can live cleanly in `Manifestation.meta` / `Work.meta` + `display` projections.
2. **Store `Work.issn` without `UNIQUE` constraint (indexed non-unique, normalized `XXXX-XXXX`):** Allows rare edge cases (e.g. merged/split serials or admin deduplication queue review via `DuplicateCandidate`) while lookup service matches normalized ISSN deterministically.
3. **Add `journal` / `periodical` aliases in `shared/format_mappings.yaml` normalizing to `magazine` (`MediaCategory.TEXT` or `MediaFormat.MAGAZINE`):** Keeps `magazine` progress statuses (`want_to_read`, `reading`, `read`, `dnf`) working seamlessly without breaking existing `text` category assumptions across facets and wishlists.

## Risks / Trade-offs

- **PostgreSQL `varchar(32)` limit on `alembic_version.version_num`** → Revision ID `v1_1_0_serial_issn_issues` is 25 chars (`<= 32`), and migration extends `v1_0_0_add_apple_id_to_users` strictly linearly (`len(heads) == 1`).
- **Existing `magazine` items without `work_kind="serial"`** → All new columns are nullable and `work_kind` defaults safely to `None`; existing books and magazines remain 100% backward-compatible.

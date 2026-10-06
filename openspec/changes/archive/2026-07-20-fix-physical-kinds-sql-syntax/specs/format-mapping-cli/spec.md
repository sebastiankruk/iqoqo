---
type: Concept
title: spec
timestamp: 2026-07-22T10:18:50Z
---

## MODIFIED Requirements

### Requirement: Apply mode updates the database using mappings

The CLI SHALL support an `--apply` mode that reads `shared/format_mappings.yaml` and performs SQL UPDATEs to fix all matching `Manifestation.meta['format']` values. The SQL statements MUST be written in a syntax compatible with both PostgreSQL and the SQLAlchemy parameter binding mechanism to avoid `SyntaxError`s during execution.

#### Scenario: Apply mode updates exact-match mappings

- **WHEN** `--apply` is invoked and `format_mappings.yaml` contains `video: dvd`
- **THEN** all manifestations with `meta['format'] = 'video'` SHALL have their `meta['format']` set to `'dvd'`
- **AND** the database operation SHALL execute successfully without syntax errors caused by bind parameter conflicts (e.g., `::text` casting).

#### Scenario: Apply mode updates NULL mappings with content-type scoping

- **WHEN** `--apply` is invoked and `format_mappings.yaml` contains `format_normalizations.null.music: cd`
- **THEN** all manifestations with `meta['format'] IS NULL` AND whose expression has `content_type = 'music'` SHALL have their `meta['format']` set to `'cd'`

#### Scenario: Apply mode reports changes made

- **WHEN** `--apply` completes successfully
- **THEN** the CLI SHALL output a summary: number of rows updated, grouped by mapping rule applied

#### Scenario: Apply mode with --dry-run previews changes without modifying

- **WHEN** `--apply --dry-run` is invoked
- **THEN** the CLI SHALL show the SQL statements that would be executed and the count of affected rows, but SHALL NOT modify the database

#### Scenario: Apply mode validates mappings before executing

- **WHEN** `--apply` is invoked and a mapping targets a non-existent `MediaFormat` value
- **THEN** the CLI SHALL exit with an error before executing any UPDATEs and SHALL report the invalid target format

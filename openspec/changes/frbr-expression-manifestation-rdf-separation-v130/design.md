## Context

Historically, iqoqo's RDF exporter attached several `Expression`-level properties directly to `m_uri` (`Manifestation`) to simplify early JSON-LD queries. As FRBRoo fidelity matured (Series, Audio, Concerts, Serials, Multi-Expression Works), attaching language, topics, and performance events to `Manifestation` causes multiple expressions of a work to misattribute properties across carriers.

## Goals / Non-Goals

- **Goals:**
  - Emit `F2_Expression` attributes strictly on `e_uri` and `F3_Manifestation` attributes strictly on `m_uri`.
  - Guarantee Work/Expression RDF endpoints enrich all child expressions/manifestations (`seen_expressions`, `seen_manifestations`).
  - Eliminate synthetic ID aliasing across FRBR tiers and stop ingest duplication across tiers.
- **Non-Goals:**
  - Dropping backwards-compatible UI display projections (API read DTOs continue flattening convenient display fields from Work/Expression when requested).

## Decisions

1. **Major-Semver SPARQL Compatibility:** Scheduled for `v1.3.0` (`minor` release bump following `1.2.0`) with documented SPARQL migration examples in `docs/SEMANTIC_WEB.md` and `docs/CHANGELOG.md`.
2. **Idempotent Cleanup Command:** Provide a non-destructive dry-run/apply script (`scripts/clean_frbr_meta_drift.py`) to strip legacy duplicated keys once verified.

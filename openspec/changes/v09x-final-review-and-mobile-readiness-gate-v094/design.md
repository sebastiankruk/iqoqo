## Context

Final milestone gate before cutting v1.0.0 branch for iOS and Android.

## Goals / Non-Goals

**Goals:**
- Zero debt carryover into mobile stream.
- Complete 100% test coverage across core guards (`ontology_validation.py`, `federation_guard.py`), custodian views (`admin/lending`), and operational scripts (`archive_orphans.py`, `generate_ai_covers.py`).

**Non-Goals:**
- Building Capacitor code in v0.9.4 (strictly reserved for v1.0.0).

## Decisions

### Multi-Agent Review Walkthrough & Test Coverage Sweep
* **Decision**: Run formal review sweep matching v0.7.18 and v0.8.4 standards, closing residual unit test gaps across backend runtime guards, custodian UI pages, and administrative CLI tools.
* **Rationale**: Guarantees code quality, prevents regression during mobile client bootstrap, and preserves ontology constraints.

## Risks / Trade-offs

- ('[Risk] Undocumented breaking API changes affecting mobile', 'Mitigation: Enforced by C87 OpenAPI contract validation.')

---
name: implementation-expert
description: "Expert skill for implementing features from code snippets OR generating plans from product improvements when code is missing."
license: AGPL
compatibility: [opencode, antigravity]
metadata: { audience: developers }
---

# Skill: Implementation Expert

## Role and Persona

You are a skilled full-stack software engineer, UI/UX designer, product manager, and product architect helping as a partner in creating a project codenamed **iqoqo** — a service enabling users to create a personal, shareable, distributed library/catalog of anything.

The project is built on top of the FRBR/FRBRoo ontology. The tech stack consists of a Python Flask backend and a React/Next.js/TypeScript frontend, backed by PostgreSQL. Background tasks are handled via Redis/Celery. It is packaged as Docker Compose orchestrations for easy deployment by anyone to eventually create a distributed digital library of everything.

## Current State

We have successfully released **v0.7.18**, concluding a comprehensive 26-chunk bottom-up codebase review (~407 files) and 6 critical hardening batches. Key improvements include: Fernet symmetric encryption at rest for InstanceSettings API secrets with automated `.env` migration (`make migrate-secrets`), a clean two-stage linear Alembic migration DAG (`v0_7_17_baseline` + `v0_7_18_fixes`), strict SQL `LIMIT`/`OFFSET` pagination and bounded query memory across items and taxonomies, SSRF cover lookup protection, TanStack Query cache invalidation harmonization with 'Coming in v0.8.0' safeguards on unwired controls, interactive operational script guardrails, a decoupled `migration` container service in Docker Compose, continuous hands-free batch scanning with audio feedback, and decoupled knowledge synchronization (`make knowledge-sync` vs `make knowledge-sync-full`, `make mykg-ask`).

## Upcoming (v0.8.0 & Beyond)

With v0.7.18 fully stabilized and verified, our sole focus is **v0.8.0: Semantic Web & Linked Open Data**. Core deliverables include: exposing FRBR collections as RDF/JSON-LD graphs, implementing a secure `/api/sparql` query endpoint via `rdflib` with an admin SPARQL explorer UI, creating complete `schema:CreativeWork` SEO mappings, enabling user Data Sovereignty Export (downloading personal libraries as canonical JSON-LD), and completing OWL/SHACL ontology validation synchronization. This directly establishes the foundation for **v0.9.0: Federation & Decentralization** (ActivityPub Inbox/Outbox endpoints, HTTP Signatures, and inter-server Trust Graph metadata sync).

## Core System Requirements

- **Data Modeling:** Strictly adhere to our extended FRBR event-based modeling for handling complex media types.
- **Search & DB:** Leverage PostgreSQL for optimized data storage and advanced Full-Text Search capabilities via `tsvector`. Check local databases prior to external identifiers.
- **API First & Security:** Maintain clean separation between the Flask API and the Next.js Web UI. Ensure strict payload validation and rate-limiting.
- **Semantic Web:** Design systems with the intent of exposing all public catalog information as Linked Open Data / RDF / JSON-LD.
- **Ingestion & Automation:** Continuously improve the scanner/camera UX and automated fallback metadata lookups.
- **Federation:** Architect the system to expose local collections with a federated network.

This skill governs codebase changes. It handles provided code OR generates required code from high-level goals.

## Core Rules

1. **Source of Truth**: `.context/notes/` is law. Plan files there override all. Do not update those files unless explicitly told so.
2. **Mirror Patterns**: Match existing style, imports, and logic exactly. No "improvements" unless asked.
3. **Type Safety**: No `# type: ignore` unless for SQLAlchemy dynamic attrs or broken external stubs. Fix the code.
4. **Environment**: Use `.venv/bin/` for all Python tools (pytest, flask, alembic).
5. **Copyright**: Every new file (.py, .ts, .tsx) MUST have the standard iqoqo AGPL header.
6. **FRBR Hierarchy**: Respect Work -> Expression -> Manifestation -> Item ontology.
7. **Context**: Discover via wikilinks in frontmatter
8. **Tests**: All new code or code changes needs to be covered with tests: backend, frontend, e2e, or script tests (BATS for shell scripts, pytest for Python scripts) - depending on their nature. Any modification to operational scripts in `scripts/` MUST be accompanied by corresponding tests in `tests/bash/` or `tests/test_scripts.py`.
9. **Refactors**: Prefer small refactors over large ones. If a large refactor is needed, it should be documented in a separate plan file and approved before implementation.
10. **Don't Mute Returns**: Do not suppress return-value warnings with `# type: ignore`, `# noqa`, or `# pylint: disable`. Handle or propagate return values properly.
11. **Preserve Docs**: When modifying existing functions, preserve all existing docstrings, comments, and type annotations. Do not strip or replace them.
12. **Non-English UI Casing**: Always use sentence case (not Title Case) for non-English localizations (e.g., Polish strings in `frontend/messages/pl.json`). Only capitalize the first word and proper nouns (e.g., "Zarządzaj kolekcjami", "Tryb konserwacji aktywny").
13. **Prohibit Heredoc / `cat << EOF` Editing**: NEVER create or edit codebase files using `cat << EOF`, `cat << 'EOF'`, or shell redirection in bash commands. Always use structured agent file manipulation tools (`replace_file_content` or dedicated file tools).
14. **Secret Encryption**: All API keys, secrets, and live OAuth tokens stored in `InstanceSettings` must use symmetric Fernet encryption derived from `SECRET_KEY`. Never persist plaintext credentials to the database.
15. **SQL Pagination**: Endpoints returning lists of entities must implement database-level SQL `LIMIT`/`OFFSET` or keyset pagination. Never use Python-level list slicing on `query.all()` or unconstrained table queries.
16. **Interactive UI Wiring**: All buttons, dropdown items, and interactive controls must be wired to functional handlers or explicitly disabled with an explanatory tooltip/badge (e.g. "Coming in v0.8.0").
17. **Migration DAG Linearity**: Keep Alembic migrations strictly linear with exactly one head. Never create branched heads or unbatched migration operations.

## Implementation Workflow

### Phase 1: Planning (If no code provided, provided code is incomplete or misaligned)

- **Explore**: Search `app/api/`, `app/core/`, `app/db/`, and `frontend/components/` for similar patterns.
- **Draft**: Create incremental snippets (patches) matching explored patterns.
- **Markers**: Use `Add to {path} after {context}:` to define insertion points.

### Phase 2: Execution

- **Apply**: Use `replace_file_content` or `multi_replace_file_content` for snippets or full files.
- **QA**: Run `make lint` and `make test`. If fail, fix code until green.
- **Cleanup**: Auto-fix lints with `ruff check --fix` or `black` without changing logic.
- **Git**: Conclude with `git add` and `git commit` using Conventional Commits.

### Phase 3: Linting and Testing

- **Linting**: `make lint` should not produce errors
- **Test** `make test` should pass.

### Phase 4: Human verification

- **Plan**: Provide plan for manual verification of changes introduced in this batch
- **Context**: Use development notes and roadmap documents (in `.context/notes/`) to highlight what needs to be verified
- **Update**: When human confirms all tests pass - you can tick corresponding checkboxes in development plan and roadmap documents to mark them as completed. If something is missing - ask human for clarification before continuing.
- **CHANGELOG**: Update CHANGELOG.md to reflect introduced changes; use current version number.

## Copyright Header

```python
# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>
#
```

Base directory for this skill: `.agents/skills/implementation-expert`
Relative paths in this skill (e.g., scripts/, reference/) are relative to this base directory.

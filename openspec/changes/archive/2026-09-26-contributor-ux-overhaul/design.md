## Context

See `proposal.md` for motivation and capability scope.

Currently in iqoqo:
1. Contributor management in the administrative catalog editor (`frontend/components/admin/frbr-editor.tsx`) is handled through free-form dynamic metadata text fields or raw JSON textareas. Catalogers must manually enter structured arrays or key-value pairs without role validation or autocomplete.
2. Contributor names entered via ingestion or manual input suffer from inconsistent capitalization. Naive title casing or uppercase input leads to improper formatting for multi-word names, hyphenated names (e.g., "Jean-Luc Godard"), initials (e.g., "J.R.R. Tolkien"), and international surnames with lowercase cultural particles (e.g., "Ludwig van Beethoven", "Ursula K. Le Guin").
3. While the database schema supports normalized FRBRoo event models (`Contributor`, `WorkContribution`, `ExpressionContribution`, `ManifestationContribution` in `app/db/contributions.py`), the core service (`app/core/frbr_service.py`) lacks unified structured agent parsing and contribution synchronization functions.
4. The admin API (`app/api/admin.py`) only transfers raw `meta` dictionaries during `get_frbr_tree` and entity `PUT` requests, omitting relational contribution models.

## Goals / Non-Goals

**Goals:**
- Provide a clean, structured UI in `FrbrEditor` where operators manage contributors as distinct rows (Role dropdown + Agent Name input + Add/Remove buttons).
- Restrict Role dropdown options strictly to valid FRBRoo roles based on entity level (Composition Event for Work, Performance Event for Expression, Publication Event for Manifestation).
- Implement a robust multi-word name capitalization utility in both frontend and backend that respects hyphenated compounds, initials, and interior lowercase cultural particles ("van", "von", "de", "da", "del", "di", "le", "la").
- Add structured agent parsing and contribution synchronization helpers (`normalize_contributor_name`, `parse_agent_input`, `sync_entity_contributions`) in `app/core/frbr_service.py`.
- Wire structured `contributions` into the Admin FRBR tree retrieval and entity update endpoints in `app/api/admin.py`.

**Non-Goals:**
- Introducing external authority file integration (e.g., VIAF, Wikidata, LCNAF) in this milestone; contributors remain locally stored in the `contributors` table.
- Changing the underlying database schema or foreign keys in PostgreSQL/SQLite.
- Adding full contributor merge or deduplication administrative tooling (relying on `get_or_create_contributor` by unique name and type).

## Decisions

### 1. Structured Contributor Form Rows in `FrbrEditor`
- **Choice**:
  - In `frontend/components/admin/frbr-editor.tsx`, replace raw dynamic metadata inputs for contributors with a dedicated `ContributorListEditor` section in `WorkEditor`, `ExpressionEditor`, and `ManifestationEditor`.
  - Each contributor row contains:
    - A `<Select>` component populated with entity-specific roles from `WORK_CONTRIBUTION_ROLES`, `EXPRESSION_CONTRIBUTION_ROLES`, and `MANIFESTATION_VIDEO_ROLES`.
    - An `<InputField>` for the contributor's display name, triggering auto-capitalization on blur.
    - A remove button (`<Trash2 />`) to delete the row.
    - A "+ Add Contributor" button to append a new row.
  - Form state tracks `contributions: Array<{ role: string; name: string; sequence: number }>`.
- **Rationale**: Form rows prevent JSON syntax errors, enforce controlled vocabularies per FRBR entity tier, and provide an intuitive workflow for catalogers.
- **Alternatives Considered**:
  - Chip/tag inputs with single global roles: Rejected because an entity can have multiple contributors with different roles (e.g., author and illustrator on the same Work).
  - Modal dialog for each contributor: Rejected because inline rows provide lower friction and immediate visibility of all contributors.

### 2. Multi-Word Name Capitalization and Particle Normalization
- **Choice**:
  - Implement `normalize_contributor_name(name: str) -> str` in `app/core/frbr_service.py` and `normalizeContributorName(name: string): string` in `frontend/components/admin/frbr-editor.tsx`.
  - Normalization logic:
    1. Strip leading and trailing whitespace; collapse internal consecutive whitespace sequences to a single space.
    2. Recognize cultural particles: `{"van", "von", "der", "den", "de", "del", "da", "di", "du", "la", "le", "lo", "te", "ter", "ten"}`.
    3. For each space-delimited word:
       - If it contains a hyphen (e.g., "Jean-Luc"), capitalize each hyphen-separated segment.
       - If it is an initial (e.g., "j." or "k."), capitalize the letter ("J.", "K.").
       - If it is an interior word (index > 0) matching a cultural particle, keep it in lowercase (e.g., "Ludwig van Beethoven"). If it is the first word, capitalize it (e.g., "Van Morrison").
       - Otherwise, capitalize the first character and keep remainder lowercase unless all-caps initials are detected.
- **Rationale**: Proper names in diverse cultural contexts (Dutch, German, French, Italian, Spanish) rely on particles that must remain lowercase in running text, whereas naive title casing produces incorrect cataloging entries.
- **Alternatives Considered**:
  - Relying on Python's `str.title()`: Rejected because it mangles apostrophes (`O'connor` vs `O'Connor`) and incorrectly capitalizes particles.
  - Adding external dependencies (`nameparser` / `titlecase`): Rejected to avoid adding heavyweight dependencies to `pyproject.toml` and `package.json` for a localized formatting utility.

### 3. Backend Structured Agent Parsing in `frbr_service.py`
- **Choice**:
  - In `app/core/frbr_service.py`, implement:
    - `parse_agent_input(raw_agents: Any, default_role: str) -> list[dict[str, Any]]`: Parses list of dicts, list of strings, or legacy comma-separated values into a uniform list of `{"name": str, "role": str, "sequence": int}`. Applies `normalize_contributor_name`.
    - `sync_entity_contributions(entity: Work | Expression | Manifestation, contributions: list[dict[str, Any]]) -> None`: Reconciles the entity's relational contributions. Finds or creates `Contributor` rows via `get_or_create_contributor(name, contributor_type)`. Adds missing contribution links, updates sequences, and removes obsolete links in a single database transaction.
  - Integrate `sync_entity_contributions` directly into `update_work`, `update_expression`, and `update_manifestation`.
- **Rationale**: Centralizing contribution synchronization in `frbr_service.py` ensures consistent data ingestion across REST APIs, admin views, and batch CLI scripts.
- **Alternatives Considered**:
  - Handling contribution synchronization inside route handlers in `app/api/admin.py`: Rejected because business logic belongs in the service layer (`frbr_service.py`) for testability and reuse.

### 4. Admin API Payload & Serialization Extension
- **Choice**:
  - In `app/api/admin.py`:
    - In `get_frbr_tree`, invoke `serialize_contributions(work, expr, manif)` and embed the serialized contribution lists in `data.work.contributions`, `data.expression.contributions`, and `data.manifestation.contributions`.
    - In `update_work`, `update_expression`, and `update_manifestation`, accept optional `contributions` payload key and pass to `frbr_service.sync_entity_contributions`.
  - In `frontend/lib/api/admin.ts`:
    - Extend `FrbrWork`, `FrbrExpression`, `FrbrManifestation`, and update DTO interfaces to type `contributions?: Array<{ role: string; name: string; sequence?: number; contributor_id?: number }>`.
- **Rationale**: Embedding contributions directly in the FRBR tree minimizes API calls and aligns with the hierarchical editor model.

## Risks / Trade-offs

- **[Risk]** Legacy catalog records store authors or publishers solely in `meta` dictionaries without corresponding rows in `work_contributions` or `manifestation_contributions`.
  → **Mitigation**: When serializing contributions in `get_frbr_tree`, if relational contribution tables have no rows for an entity, fall back to parsing legacy `meta.authors`, `meta.author`, or `meta.publisher` via `parse_agent_input` so existing metadata is displayed in the form rows.
- **[Risk]** Over-aggressive name normalization altering intentional capitalization (e.g., acronyms or artist pseudonyms like "e.e. cummings" or "deadmau5").
  → **Mitigation**: Normalization trims whitespace and handles standard particles while allowing manual overrides if explicit casing is provided.
- **[Risk]** Concurrent editing of an entity's contributors causing sequence or deletion conflicts.
  → **Mitigation**: Contribution synchronization executes within an atomic SQLAlchemy database transaction, replacing existing links idempotently.

## Migration Plan

1. Deploy backend changes to `frbr_service.py` and `app/api/admin.py` (backward-compatible; accepts both old and new payload shapes).
2. Deploy frontend updates to `frbr-editor.tsx` and API clients.
3. No database schema migrations are necessary; existing tables and indexes in `catalog` schema are reused.
4. Rollback strategy: Frontend and backend components can be rolled back independently without database schema reversal.

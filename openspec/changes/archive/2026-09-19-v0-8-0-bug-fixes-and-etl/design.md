## Context

See `proposal.md` for problem motivation and capability scope.

Currently, iqoqo exhibits several data integrity and presentation gaps:
1. Ingested catalog records from sources such as Google Books, OpenLibrary, and Discogs include descriptions formatted in HTML or Markdown. The frontend (`frontend/components/item/extended-metadata.tsx`) wraps these inside a Tailwind Typography `prose` container but renders `{description}` verbatim in a `<p>` tag, causing raw HTML tags (e.g., `<p>`, `<b>`, `<i>`, `<br/>`) or markdown markers to leak visually to users.
2. In `frontend/components/admin/frbr-editor.tsx`, the Expression editor form suffers from value binding mismatches between React state (`type`, `kind`) and native `<select>` options, leading to auto-selection bugs and potential empty value submission during entity updates.
3. Diverse historical ingestion paths have introduced data drift: orphaned expressions/manifestations/items, duplicate manifestation records created from varied ISBN-10/ISBN-13 formats, and ISBNs erroneously stored on `Work` entities instead of `Manifestation` entities.
4. Operational scripts and Makefile targets are needed to audit and repair these integrity anomalies reliably with automated backup guarantees.
5. The `/profile` page contains the Data Sovereignty RDF Export card (C6) and GDPR privacy consent toggles, but no navigation link in the UI points to this route. Meanwhile, `/admin/settings` serves as a "unified settings hub" with a role-gated sidebar (Profile tab for all users, Custodian/Admin tabs for privileged roles), but lacks the RDF export button and GDPR consents. The desktop dropdown and mobile bottom nav both label their links "Profile" / "Profile Settings" but point to `/admin/settings`, making the export feature completely unreachable.

## Goals / Non-Goals

**Goals:**
- Provide safe client-side sanitization and rendering of rich text descriptions using `dompurify` and `react-markdown`.
- Fix value binding and auto-selection in `FrbrEditor` Expression dropdowns.
- Implement `scripts/audit_frbr_integrity.py` to detect orphans, duplicates, and ISBN violations with CI-friendly exit codes and JSON reporting.
- Implement `scripts/etl_frbr_strict.py` to reconcile duplicates, normalize ISBN-10 to ISBN-13, relocate misplaced ISBNs, and execute with backup-first guarantees and dry-run support.
- Add operational Makefile targets: `audit-frbr`, `etl-frbr`, and `sync-ontology`.
- Consolidate user-facing profile features into `/profile` (username, bio, avatar, visibility, RDF export, GDPR consents) and restrict `/admin/settings` to admin-only access. Fix all navigation links to point to the correct routes with role-based visibility.

**Non-Goals:**
- Implementing a full rich-text WYSIWYG editor for end-user writing (focus is strictly on safe rendering of catalog metadata).
- Deleting physical copy items during entity reconciliation (items are always reparented to canonical manifestations).
- Rewriting the FRBR editor component hierarchy from scratch.

## Decisions

### 1. Frontend Rich Text Rendering Architecture (`dompurify` + `react-markdown`)
- **Choice**:
  - Install `dompurify`, `@types/dompurify`, and `react-markdown` in `frontend/`.
  - In `ExtendedMetadata` (and shared description renderers), sanitize incoming HTML/markdown with `DOMPurify.sanitize()` allowing standard formatting tags (`<b>`, `<i>`, `<em>`, `<strong>`, `p`, `br`, `ul`, `ol`, `li`, `a`).
  - Render markdown syntax via `react-markdown` for non-HTML descriptions or descriptions with mixed markdown.
- **Rationale**: External metadata providers deliver mixed content (some HTML, some markdown, some plain text). Sanitizing with DOMPurify eliminates XSS vulnerabilities while `react-markdown` renders formatting cleanly.
- **Alternatives Considered**:
  - Pure regex tag stripping: Rejected because it destroys legitimate formatting and is vulnerable to evasion.
  - `dangerouslySetInnerHTML` without DOMPurify: Rejected due to high XSS risk from external ingestion payloads.

### 2. FRBR Editor Expression Value Binding (R10)
- **Choice**:
  - In `ExpressionEditor` (`frontend/components/admin/frbr-editor.tsx`), ensure `initialType` and `initialKind` reliably map to controlled option values.
  - Add explicit placeholder/default option handling for content type and kind to prevent browser auto-selection divergence.
  - Bind `value` and `onChange` strictly to local state and synchronize when `tree.expression` props update.
- **Rationale**: React uncontrolled-to-controlled or uninitialized `<select>` elements default to the first child `<option>` in the DOM without updating component state, causing silent submission of default or stale values.
- **Alternatives Considered**: Refactoring entire editor to Radix `Select`. Rejected to avoid unnecessary UI changes and minimize regression risks in existing tests.

### 3. FRBR Integrity Audit Script (`scripts/audit_frbr_integrity.py`)
- **Choice**:
  - Implement read-only CLI script with Flask application context.
  - Checks performed:
    1. **Orphans**: `Expression` without `Work`, `Manifestation` without `Expression`, `Item` without `Manifestation`.
    2. **Duplicates**: `Manifestation` rows with identical normalized ISBNs; `Work` rows with identical normalized titles and authors.
    3. **ISBN Violations**: Invalid lengths, invalid check digits (modulo 10 / modulo 11), and ISBNs present in `Work.meta` instead of `Manifestation`.
  - CLI flags: `--json` for machine-readable output, `--verbose` for detailed entity dumps. Exit code `0` if clean, `1` if violations found.
- **Rationale**: Enables both manual developer inspection and automated CI / cron monitoring.
- **Alternatives Considered**: Direct SQL queries in a bash script. Rejected because SQLAlchemy model introspection provides dialect independence (Postgres & SQLite) and reuses core model relationships.

### 4. Strict FRBR ETL Script (`scripts/etl_frbr_strict.py`)
- **Choice**:
  - Implement a transactional CLI script with safety flags: `--dry-run` (default or optional flag), `--backup` (enabled by default), and `--skip-backup`.
  - **Backup Safety**: Prior to applying database mutations, invokes the database backup mechanism (or creates a point-in-time snapshot) and verifies backup file creation. Aborts immediately if backup fails.
  - **Normalization**:
    - Converts ISBN-10 to ISBN-13 (prepending `978` and recalculating the EAN-13 check digit).
    - Strips hyphens, spaces, and formatting characters from `isbn13`.
    - Relocates any `isbn` / `isbn13` found in `work.meta` to the child `manifestation.isbn13` column.
  - **Duplicate Merging**:
    - Groups duplicate manifestations by normalized `isbn13`.
    - Selects canonical manifestation (oldest record or record with highest item count).
    - Reassigns all `Item.manifestation_id` foreign keys to the canonical manifestation.
    - Merges unique tags and metadata fields into canonical manifestation.
    - Safely deletes duplicate manifestation records.
- **Rationale**: Guarantees zero data loss, preserves physical item associations, and ensures operations are completely idempotent.
- **Alternatives Considered**: Simple `DELETE` of duplicates. Rejected because attached physical copies (Items) would either be orphaned or deleted via cascade.

### 5. Makefile Operations Standardization
- **Choice**: Add three standardized targets to `Makefile`:
  - `audit-frbr`: Executes `$(PYTHON_CMD) scripts/audit_frbr_integrity.py`
  - `etl-frbr`: Executes `$(PYTHON_CMD) scripts/etl_frbr_strict.py`
  - `sync-ontology`: Executes `$(PYTHON_CMD) scripts/sync_ontology.py`
- **Rationale**: Unifies developer experience across local virtualenv and Docker Compose environments using the existing `PYTHON_CMD` abstraction.

### 6. Profile Navigation Unification and Route Access Split
- **Choice**:
  - Consolidate all user-facing profile features into `/profile`: merge username, bio, avatar URL, and profile visibility editing (currently in `/admin/settings` Profile tab) alongside existing display name, RDF export, GDPR consents, escalations, logout, and delete account.
  - Gate `/admin/settings` behind admin role check, removing its "Profile" tab. Non-admin users accessing `/admin/settings` are redirected to `/profile`.
  - Fix navigation in `frontend/components/dashboard/navbar.tsx`:
    - Desktop dropdown: rename "Profile Settings" to "Profile", change href to `/profile`. Show "Admin Settings" (`/admin/settings`) only for admin role.
    - Mobile bottom bar: change "Profile" href from `/admin/settings` to `/profile`.
    - Fix active state highlighting to match `/profile` pathname.
  - Fix admin sub-page sidebars (`groups/page.tsx`, `content/page.tsx`) to point "Profile" NavItem to `/profile`.
  - Extract shared components (e.g., `ExportCollectionCard`, `GdprConsentsCard`) if reuse is needed across pages.
- **Rationale**: The data-sovereignty-export change placed the RDF export UI on `/profile`, but navigation was never updated. Regular users cannot discover or use their data export rights. The `/admin/settings` path under `/admin/` implies admin-only access, violating user expectations. Separating user-facing profile from admin-only settings follows the principle of least privilege and standard UX patterns.
- **Alternatives Considered**:
  - Merging everything into `/admin/settings` and redirecting `/profile` there: rejected because placing user-facing features under `/admin/` path is semantically misleading and confuses regular users.
  - Adding RDF export to `/admin/settings` without fixing navigation: rejected because it doesn't solve the underlying route confusion and leaves GDPR consents orphaned.

## Risks / Trade-offs

- **[Risk] DOMPurify SSR compatibility issues in Next.js** → Mitigation: Import `dompurify` dynamically or use `isomorphic-dompurify` so sanitization executes seamlessly on both server and client.
- **[Risk] Production database lock during large ETL runs** → Mitigation: Process entity deduplication in batched transactions (chunks of 200 records) with explicit commit points.
- **[Risk] Backup failure blocking ETL in test or container environments without external storage** → Mitigation: Support `--skip-backup` flag explicitly intended for test pipelines and local SQLite runs.
- **[Risk] Duplicate profile editing state between pages during transition** → Mitigation: Extract shared profile form state into a custom hook (`useProfileForm`) to avoid divergence.

## Migration Plan

1. Install frontend dependencies: `npm --prefix frontend install dompurify @types/dompurify react-markdown`.
2. Apply frontend description rendering and FRBR editor binding fixes.
3. Deploy `scripts/audit_frbr_integrity.py` and `scripts/etl_frbr_strict.py`.
4. Update `Makefile` with `audit-frbr`, `etl-frbr`, and `sync-ontology`.
5. Run `make audit-frbr` to record initial violation metrics.
6. Run `make etl-frbr` in dry-run mode to verify planned operations, then apply live.
7. Re-run `make audit-frbr` to confirm complete resolution.

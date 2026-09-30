## Why

Catalog data ingested from diverse external providers often introduces anomalies—orphaned records, duplicate entities, malformed ISBNs, or ISBNs misplaced at the Work level rather than Manifestation level—that compromise FRBR integrity. Simultaneously, description fields containing HTML or Markdown currently render verbatim in frontend views, while the FRBR editor Expression dropdown suffers from binding discrepancies during entity updates. This change delivers C7 in the v0.8.0 release milestone to resolve these critical bug fixes and introduce hardened, idempotent FRBR data integrity scripts with operational Makefile targets.

## What Changes

- **Safe Rich Text & Markdown Rendering (D3)**: Integrate `dompurify` and `react-markdown` to sanitize and safely render rich text descriptions in `ExtendedMetadata` and related item views without raw markup leaking.
- **FRBR Editor Expression Value Binding (R10)**: Fix two-way state and value binding for Expression dropdowns in `FrbrEditor` to ensure accurate entity pre-selection and synchronization on save.
- **FRBR Integrity Audit Script (`scripts/audit_frbr_integrity.py`)**: Implement an operational audit CLI that detects orphaned Expressions/Manifestations/Items, duplicate entities, and ISBN hierarchy/checksum violations.
- **Strict FRBR ETL Script (`scripts/etl_frbr_strict.py`)**: Implement a robust, idempotent ETL script that merges duplicate entities, normalizes ISBN-10 to standard ISBN-13, relocates misplaced ISBN attributes to Manifestations, and performs an automated database backup prior to execution.
- **Operational Makefile Targets**: Add `audit-frbr`, `etl-frbr`, and `sync-ontology` targets to standardize operations in developer and deployment environments.
- **Profile Navigation Unification (N1)**: Consolidate user-facing profile features (username, bio, avatar, visibility editing from `/admin/settings` Profile tab; RDF export and GDPR consents already on `/profile`) into `/profile` as the single user hub. Restrict `/admin/settings` to admin-only access. Fix all navigation links in `navbar.tsx` so "Profile" points to `/profile` and "Settings" is admin-gated.

## Capabilities

### New Capabilities
- `operations/frbr-etl`: FRBR database integrity auditing, duplicate entity reconciliation, ISBN-13 normalization, and automated backup-first ETL operations.
- `editor/rich-text-rendering`: Secure client-side sanitization and markdown rendering for catalog descriptions and reliable FRBR editor form bindings.
- `navigation/profile-settings-split`: Navigation route unification separating user-facing `/profile` from admin-only `/admin/settings` with role-based link visibility and feature consolidation.

### Modified Capabilities
<!-- None: core FRBR ontology boundaries remain intact; this introduces operational ETL tooling and rich text UI rendering capabilities -->

## Impact

- **Frontend**:
  - `frontend/package.json`: Add dependencies for `dompurify` (and `@types/dompurify`) and `react-markdown`.
  - `frontend/components/item/extended-metadata.tsx`: Replace raw `<p>{description}</p>` with sanitized markdown rendering.
  - `frontend/components/admin/frbr-editor.tsx`: Fix Expression dropdown selection binding.
  - `frontend/components/dashboard/navbar.tsx`: Fix desktop dropdown "Profile Settings" and mobile bottom bar "Profile" to link to `/profile`; render "Admin Settings" link conditionally for admin role only.
  - `frontend/app/profile/page.tsx`: Consolidate username, bio, avatar URL, and profile visibility editing from `/admin/settings` Profile tab.
  - `frontend/app/admin/settings/page.tsx`: Remove "Profile" tab from sidebar; add admin role gate (redirect non-admin users).
  - `frontend/app/admin/groups/page.tsx`, `frontend/app/admin/content/page.tsx`: Fix sidebar "Profile" NavItem links to point to `/profile`.
- **Backend & Scripts**:
  - `scripts/audit_frbr_integrity.py`: New CLI script for read-only database integrity checks.
  - `scripts/etl_frbr_strict.py`: New CLI script for idempotent data normalization with backup safety.
- **Build & Operations**:
  - `Makefile`: Add `audit-frbr`, `etl-frbr`, and `sync-ontology` targets.
- **Breaking Changes**: None. All changes are backward-compatible bug fixes and operational tools.

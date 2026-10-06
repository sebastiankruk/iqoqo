## Why

Cataloging contributors (authors, composers, performers, directors, publishers) in the FRBR Editor currently requires editing unformatted JSON textareas or stringified metadata fields. This workflow is error-prone, provides zero validation against FRBRoo controlled vocabularies, and forces administrators to memorize schema keys. Furthermore, multi-word contributor names (e.g., compound names, hyphenated names, lowercase cultural particles) suffer from inconsistent capitalization, and the backend lacks structured agent parsing in `frbr_service.py` to cleanly normalize names and map them to their corresponding FRBRoo event entities. Delivering C9 in the v0.8.1 milestone overhauls this experience with dedicated structured form rows, robust multi-word name capitalization, and backend agent synchronization.

## What Changes

- **Structured Contributor Form Rows**: Replace JSON textareas and ad-hoc dynamic metadata inputs in `FrbrEditor` with structured contributor rows consisting of a validated Role dropdown and an Agent Name text field, supporting addition, deletion, and sequence ordering.
- **FRBRoo-Aware Role Selection**: Scope the Role dropdown options by FRBR entity level: Composition Event roles for Works (`author`, `composer`, `lyricist`, `director`, `writer`), Performance Event roles for Expressions (`performer`, `narrator`, `conductor`, `actor`), and Publication Event roles for Manifestations (`publisher`, `studio`, `distributor`).
- **Multi-Word Name Capitalization**: Implement intelligent name capitalization utility that handles multi-word names, hyphenated names (e.g., "Jean-Luc Godard"), initials (e.g., "Ursula K. Le Guin"), and preserves international lowercase particles (e.g., "van", "von", "de", "di", "da", "del").
- **Backend Structured Agent Parsing (`frbr_service.py`)**: Introduce structured agent parsing and synchronization functions in `frbr_service.py` (`parse_agent_input`, `sync_entity_contributions`) that parse list-of-dicts payloads, normalize and capitalize agent names, get-or-create `Contributor` rows, and upsert the corresponding FRBRoo contribution records.
- **FRBR Admin API Integration**: Extend FRBR tree retrieval and entity update endpoints in `app/api/admin.py` to ingest and return structured `contributions` arrays alongside entity metadata while preserving backward compatibility with legacy payloads.

## Capabilities

### New Capabilities
- `editor/contributor-ux`: Structured contributor input interface featuring role selection, multi-word name capitalization, and backend agent parsing across FRBR entities.

### Modified Capabilities
<!-- None: core FRBR ontology hierarchy remains intact; this change enhances editor input UX and structured contributor event management -->

## Impact

- **Frontend**:
  - `frontend/components/admin/frbr-editor.tsx`: Replace raw JSON textareas with structured `ContributorRow` components (Role dropdown + Name input), integrate name capitalization helper, and bind contributor state.
  - `frontend/lib/api/admin.ts`: Update TypeScript interfaces (`WorkFormData`, `ExpressionFormData`, `ManifestationFormData`, `FrbrTree`) to carry structured `contributions`.
  - `frontend/__tests__/components/admin/frbr-editor.test.tsx` & `frontend/tests/frbr-editor.test.tsx`: Add test coverage for adding, editing, removing contributor rows and verifying API payloads.
- **Backend**:
  - `app/core/frbr_service.py`: Add `normalize_contributor_name`, `parse_agent_input`, and `sync_entity_contributions` helper functions.
  - `app/api/admin.py`: Update `get_frbr_tree`, `update_work`, `update_expression`, and `update_manifestation` to handle structured contributor payloads.
  - `tests/test_admin_frbr.py` & `tests/test_frbr_events.py`: Add test cases for contributor parsing, capitalization edge cases, and contribution persistence.
- **Dependencies & Schemas**: No database migration required; reuses existing `contributors`, `work_contributions`, `expression_contributions`, and `manifestation_contributions` tables.
- **Breaking Changes**: None. Legacy string arrays or JSON representations in `meta` continue to be parsed gracefully.

## Purpose

Automates the identification of duplicate Works and Manifestations using local LLM inference, maintains a review queue of candidate matches, and provides safe, atomic administrative merge workflows that preserve FRBR hierarchy integrity.

## ADDED Requirements

### Requirement: Candidate Duplicate Generation and Heuristic Screening
The duplicate detection system MUST identify candidate pairs of Works and Manifestations using heuristic metadata comparison (such as normalized titles, sort titles, author contributions, and publication dates) before invoking language model evaluation, filtering candidate pairs to prevent unnecessary LLM inference requests.

#### Scenario: High-similarity Works identified as candidate pairs
- **WHEN** two Works share identical or highly similar normalized titles and overlapping creator credits
- **THEN** the system flags the pair as candidate duplicate Works and queues them for LLM evaluation.

#### Scenario: Candidate Manifestations identified under differing or identical Expressions
- **WHEN** two Manifestations have matching or closely variant titles, formats, or ISBN attributes
- **THEN** the system flags the pair as candidate duplicate Manifestations and queues them for LLM evaluation.

### Requirement: LLM-Assisted Duplicate Analysis and Scoring
The duplicate detection service MUST evaluate candidate pairs using a local LLM (via Ollama API) to analyze semantic identity, determine a confidence score between 0.0 and 1.0, and provide a structured explanation rationale. If the Ollama service is unreachable or returns an error, the system MUST log a diagnostic warning, record the failure, and avoid interrupting catalog operations.

#### Scenario: Successful LLM candidate evaluation
- **WHEN** the duplicate detection service submits a candidate pair of Works with metadata to Ollama
- **THEN** the LLM returns a similarity evaluation containing a numeric confidence score, match verdict, and textual rationale.

#### Scenario: Ollama service unavailable during detection run
- **WHEN** the duplicate detection service attempts to evaluate a candidate pair while Ollama is unreachable
- **THEN** the system records an evaluation failure error, continues processing remaining candidates, and leaves the candidate status pending without crashing.

### Requirement: Duplicate Candidate Persistence and Lifecycle Management
The system MUST persist detected duplicate candidate pairs in a database table with attributes including source entity ID, target entity ID, entity tier (`work` or `manifestation`), confidence score, LLM reasoning rationale, detection timestamp, and review status (`pending`, `merged`, `dismissed`).

#### Scenario: Storing newly detected duplicate candidate
- **WHEN** the detection process identifies a candidate pair with confidence above the detection threshold
- **THEN** the system creates a `DuplicateCandidate` record with `pending` status and stores the LLM analysis rationale.

#### Scenario: Preventing duplicate candidate pair re-creation
- **WHEN** a candidate pair that was previously dismissed or merged is detected again in a subsequent scan
- **THEN** the system does not create a redundant candidate record or re-queue the dismissed pair.

### Requirement: Administrative Review and Candidate Queue API
The system MUST provide authenticated administrative REST endpoints under `/api/v1/admin/duplicates` allowing authorized administrators to list pending duplicate candidates with pagination and filtering by entity tier or confidence score, dismiss false positive candidates, and trigger manual detection scans.

#### Scenario: Administrator retrieves pending duplicate candidates
- **WHEN** an authenticated administrator sends a GET request to `/api/v1/admin/duplicates?status=pending`
- **THEN** the server returns a paginated list of candidate pairs with their entity metadata, confidence scores, and LLM reasoning.

#### Scenario: Non-admin user denied access to duplicate management
- **WHEN** an unauthenticated or non-admin user requests `/api/v1/admin/duplicates`
- **THEN** the server rejects the request with HTTP 401 Unauthorized or HTTP 403 Forbidden.

#### Scenario: Dismissing a false positive duplicate candidate
- **WHEN** an administrator posts a dismissal request to `/api/v1/admin/duplicates/<id>/dismiss`
- **THEN** the system updates the candidate status to `dismissed` and records the dismissing administrator's identity.

### Requirement: FRBR-Compliant Work Merging
The system MUST provide an atomic administrative merge action for duplicate Works at `/api/v1/admin/duplicates/<id>/merge` that transfers all child Expressions from the secondary Work to the primary Work, re-links associated Work contributions and expansion links, archives or deletes the secondary Work, records an entry in `EntityAuditLog`, and transitions the candidate status to `merged`. Merging MUST NEVER bypass the FRBR hierarchy or orphan Expressions.

#### Scenario: Merging duplicate Works re-parents child Expressions
- **WHEN** an administrator confirms the merge of secondary Work B into primary Work A
- **THEN** all Expressions previously associated with Work B are updated to reference Work A as their parent `work_id`, Work B is removed from active catalog queries, and an audit log records the merge event.

#### Scenario: Transaction rollback upon merge failure
- **WHEN** a database error occurs during Expression re-parenting or relationship updating
- **THEN** the entire merge transaction rolls back cleanly, leaving all Works and Expressions in their original state.

### Requirement: FRBR-Compliant Manifestation Merging
The system MUST provide an atomic administrative merge action for duplicate Manifestations that transfers all child Items from the secondary Manifestation to the primary Manifestation, merges or reconciles manifestation-level contributions, preserves `isbn13` and edition attributes exclusively on the primary Manifestation entity, archives or deletes the secondary Manifestation, records an entry in `EntityAuditLog`, and transitions the candidate status to `merged`. Merging MUST NEVER bypass the FRBR hierarchy or orphan Items.

#### Scenario: Merging duplicate Manifestations re-parents child Items
- **WHEN** an administrator confirms the merge of secondary Manifestation B into primary Manifestation A
- **THEN** all Items previously referencing Manifestation B are updated to reference Manifestation A as their parent `manifestation_id`, Manifestation B is removed, and an audit log entry is written.

#### Scenario: Validating ISBN attribution strictly on Manifestations
- **WHEN** duplicate Manifestations are merged
- **THEN** the target Manifestation retains valid ISBN identifiers on the Manifestation entity (F3), and no ISBN attribute is assigned to parent Works or Expressions.

### Requirement: Admin Duplicate Review Interface
The admin web interface MUST provide a dedicated Duplicate Review view at `/admin/duplicates` that displays pending candidate pairs side-by-side with entity metadata, cover images, hierarchy details (associated Expressions or Items), confidence badge, and LLM reasoning, allowing administrators to select which entity to retain as primary and execute the merge or dismiss the candidate.

#### Scenario: Side-by-side candidate inspection
- **WHEN** an administrator navigates to `/admin/duplicates` and selects a pending candidate pair
- **THEN** the interface displays both entities side by side with titles, creators, FRBR hierarchy children, and the LLM's explanation for the match.

#### Scenario: Executing merge from administrative interface
- **WHEN** an administrator selects the primary entity and clicks "Merge Duplicates" in the confirmation dialog
- **THEN** the UI submits the merge request, shows a progress indicator, displays a success toast upon completion, and removes the resolved candidate from the pending list.

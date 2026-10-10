## MODIFIED Requirements

### Requirement: Candidate Duplicate Generation and Heuristic Screening

The duplicate detection system MUST identify candidate pairs of Works, Expressions, and Manifestations using heuristic metadata comparison (such as normalized titles, sort titles, author contributions, and publication dates) before invoking language model evaluation, filtering candidate pairs to prevent unnecessary LLM inference requests. Every surviving pair MUST then pass through the deterministic classifier, which assigns exactly one verdict — `AUTO_ACCEPT`, `AUTO_REJECT`, or `NEEDS_LLM` — and MUST NOT route a pair to inference that a deterministic rule already decides.

For the Expression tier the system MUST derive blocking keys from the Expression's own identity — its normalized label together with its `(language, content_type)` pair — and MUST NOT fall back to the parent Work's title or sort title, because every Expression of a Work inherits those and would therefore block against every other. A pair whose `language` or `content_type` differs MUST be discarded before scoring and MUST NOT be queued. An Expression label is the F2 realization's own name and is not required to be present, so a pair whose labels are both absent is not a candidate.

#### Scenario: High-similarity Works identified as candidate pairs
- **WHEN** two Works share identical or highly similar normalized titles and overlapping creator credits
- **THEN** the system flags the pair as candidate duplicate Works and applies the deterministic classifier verdict.

#### Scenario: Candidate Manifestations identified under differing or identical Expressions
- **WHEN** two Manifestations have matching or closely variant titles, formats, or ISBN attributes
- **THEN** the system flags the pair as candidate duplicate Manifestations and applies the deterministic classifier verdict.

#### Scenario: Shared edition identifier accepts the pair without inference
- **WHEN** two Manifestations carry the same non-null value in a shared edition identifier field and no classifier rule contradicts it
- **THEN** the system assigns `AUTO_ACCEPT`, queues the pair for review without calling an inference service, and records the deciding rule.

#### Scenario: Identical title with a shared creator is not sufficient to auto-accept
- **WHEN** two Works have an identical normalized title and a shared creator but no shared edition identifier and no other agreeing field
- **THEN** the system assigns `NEEDS_LLM` rather than `AUTO_ACCEPT`.

#### Scenario: Two distinct works sharing a common title
- **WHEN** two Works are both titled "Greatest Hits" with no shared creator
- **THEN** the system does not treat the shared title as evidence of duplication.

#### Scenario: A scan completes with no inference service reachable
- **WHEN** a scan runs under the default `heuristic` engine while the inference service is unreachable
- **THEN** the scan completes and reports per-verdict counts, and no inference request is attempted.

#### Scenario: Realizations of one Work are screened against their own labels
- **WHEN** two Expressions of the same Work share a `language` and a `content_type` and have identical normalized labels
- **THEN** the system flags the pair as candidate duplicate Expressions and queues them for review.

#### Scenario: Expressions of one Work are never paired on the inherited Work title
- **WHEN** a scan runs over a Work that has several Expressions in different languages
- **THEN** no pair of those Expressions is queued merely because they share the parent Work's title.

#### Scenario: Distinct realizations of one Work are never paired
- **WHEN** two Expressions of the same Work differ in `language` or `content_type`
- **THEN** the system discards the pair before scoring, and no candidate row is created for it.

### Requirement: Duplicate Candidate Persistence and Lifecycle Management

The system MUST persist detected duplicate candidate pairs in a database table with attributes including source entity ID, target entity ID, entity tier (`work`, `expression`, or `manifestation`), confidence score, LLM reasoning rationale, detection timestamp, and review status (`pending`, `merged`, `dismissed`). The stored `entity_tier` MUST be constrained at the database level to those three values, and a candidate queued by the deterministic classifier rather than a language model MUST carry a NULL confidence together with a `resolution_source` recording which stage decided it.

#### Scenario: Storing newly detected duplicate candidate
- **WHEN** the detection process queues a candidate pair, whether from inference scoring or from a deterministic rule
- **THEN** the system creates a `DuplicateCandidate` record with `pending` status and records the deciding stage in `resolution_source`.

#### Scenario: Rejecting a tier outside the vocabulary
- **WHEN** a candidate is created with an `entity_tier` outside `work`, `expression`, and `manifestation`
- **THEN** the system rejects it, and the database check constraint rejects a direct write.

#### Scenario: A rule verdict carries no probability
- **WHEN** the deterministic classifier queues a pair
- **THEN** the stored `confidence` is NULL and `resolution_source` is `heuristic`, so no categorical verdict is presented as a calibrated probability.

#### Scenario: An inference verdict carries both a score and its provenance
- **WHEN** a language model queues a pair
- **THEN** the stored `confidence` is the model's score, `resolution_source` is `llama`, and the rationale is retained.

#### Scenario: Rows predating provenance are backfilled
- **WHEN** a candidate row exists with no `resolution_source` and no LLM rationale
- **THEN** the migration sets `resolution_source` to `heuristic` for that row.

#### Scenario: Preventing duplicate candidate pair re-creation
- **WHEN** a candidate pair that was previously dismissed or merged is detected again in a subsequent scan
- **THEN** the system does not create a redundant candidate record or re-queue the dismissed pair.

### Requirement: Administrative Review and Candidate Queue API

The system MUST provide authenticated REST endpoints under `/api/v1/admin/duplicates` allowing authorized users to list candidates with pagination and filtering by entity tier or status, dismiss false positive candidates, execute merges, and trigger manual detection scans. Access MUST be authorized by permission rather than by role: listing requires `read:metadata`, while scanning, dismissing, and merging require `write:metadata`. The listing MUST accept `expression` as an entity-tier filter, and the scan trigger MUST accept `expression` as a tier.

#### Scenario: Administrator retrieves pending duplicate candidates
- **WHEN** an authenticated user holding `read:metadata` sends a GET request to `/api/v1/admin/duplicates?status=pending`
- **THEN** the server returns a paginated list of candidate pairs with their entity metadata, confidence (nullable), `resolution_source`, and LLM reasoning.

#### Scenario: Non-admin user denied access to duplicate management
- **WHEN** an unauthenticated user, or an authenticated user without `read:metadata`, requests `/api/v1/admin/duplicates`
- **THEN** the server rejects the request with HTTP 401 Unauthorized or HTTP 403 Forbidden.

#### Scenario: A read-only contributor cannot merge
- **WHEN** an authenticated user holding only `read:metadata` posts a merge to `/api/v1/admin/duplicates/<id>/merge`
- **THEN** the server rejects the request with HTTP 403 Forbidden and no entity is modified.

#### Scenario: Excessive merge requests are rate limited
- **WHEN** a client exceeds the configured merge rate limit
- **THEN** the server responds with HTTP 429 Too Many Requests and performs no further merges.

#### Scenario: Dismissing a false positive duplicate candidate
- **WHEN** a user holding `write:metadata` posts a dismissal request to `/api/v1/admin/duplicates/<id>/dismiss`
- **THEN** the system updates the candidate status to `dismissed` and records the dismissing user's identity.

#### Scenario: Listing candidates filtered to the Expression tier
- **WHEN** a client requests pending candidates with `entity_tier=expression`
- **THEN** the response contains only Expression-tier candidates, with the total reflecting that filter.

#### Scenario: Scanning only the Expression tier
- **WHEN** a client triggers a scan with `tier: "expression"`
- **THEN** only Expressions are screened, and no Work or Manifestation candidate is created by that run.

#### Scenario: Rejecting an unsupported tier
- **WHEN** a client requests a tier outside `work`, `expression`, `manifestation`, and `all`
- **THEN** the system responds with a validation error and creates nothing.


### Requirement: Admin Duplicate Review Interface

The admin web interface MUST provide a dedicated Duplicate Review view at `/admin/duplicates` that displays pending candidate pairs side-by-side with entity metadata, cover images, hierarchy details (associated Expressions or Items), a provenance-labelled confidence badge, and the reasoning that produced the candidate, allowing administrators to select which entity to retain as primary and execute the merge or dismiss the candidate. A candidate queued by the deterministic classifier carries no probability and MUST be presented as a categorical decision with its reasons, never as a model confidence percentage. Adding the Expression tier MUST NOT add controls to the candidate card.

#### Scenario: Side-by-side candidate inspection
- **WHEN** an administrator navigates to `/admin/duplicates` and selects a pending candidate pair
- **THEN** the interface displays both entities side by side with titles, creators, FRBR hierarchy children, and the reasoning for the match.

#### Scenario: Executing merge from administrative interface
- **WHEN** an administrator selects the primary entity and confirms the merge in the confirmation dialog
- **THEN** the UI submits the merge request, shows a progress indicator, displays a success toast upon completion, and removes the resolved candidate from the pending list.

#### Scenario: The decision badge names the stage that made it
- **WHEN** the review queue displays a candidate decided by the deterministic classifier and one decided by a language model
- **THEN** the rule verdict's badge carries no percentage, and the model verdict's badge is labelled as a model confidence.

#### Scenario: A candidate with no confidence does not render as zero percent
- **WHEN** the review queue displays a candidate whose confidence is NULL
- **THEN** the badge presents the pair as a match rather than as a `0%` match.

#### Scenario: Empty state does not imply inference is required
- **WHEN** an administrator opens the review queue with no pending candidates
- **THEN** the empty-state copy states that a scan can be resolved from the records alone and points to the `llama` engine for the remaining grey zone.

#### Scenario: Destructive controls are hidden from viewers
- **WHEN** a user without `write:metadata` opens the review queue
- **THEN** the dismiss and merge controls are absent, while the side-by-side comparison remains available.

#### Scenario: Classifier provenance is labelled distinctly
- **WHEN** a candidate was queued by the deterministic classifier and has a NULL confidence
- **THEN** the interface presents it as a classifier decision with its reasons, not as a confidence percentage.

#### Scenario: Reviewing an Expression candidate
- **WHEN** a pending candidate is an Expression-tier pair
- **THEN** the interface compares the two Expressions by label, language, content type, child Manifestation count, and creators, using the same card and the same number of controls as the Work and Manifestation tiers.

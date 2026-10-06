# operations/duplicate-detection — Delta for frbr-merge-consolidation

Track 2 of this change made inference optional and added provenance to the
candidate record. Those are changes to this capability, not to merge integrity,
so they are recorded here. `frbr/merge-integrity` carries the merge mechanics
and the classifier's thresholds; this file records what the candidate record and
the scan contract now guarantee.

The tier vocabulary stays `work` and `manifestation` here. Widening it to
`expression` is v0.8.3 work (change `duplicate-expression-tier`).

## MODIFIED Requirements

### Requirement: Candidate Duplicate Generation and Heuristic Screening

The duplicate detection system MUST identify candidate pairs of Works and Manifestations using heuristic metadata comparison (such as normalized titles, sort titles, author contributions, and publication dates) before invoking language model evaluation, filtering candidate pairs to prevent unnecessary LLM inference requests. The system MUST then apply a deterministic classifier to each pair before any inference, assigning exactly one verdict — `AUTO_ACCEPT` when the pair shares an edition-family identifier, or when it has an identical normalized title and at least one shared creator; `AUTO_REJECT` when the pair shares a creator but scores below the title floor; or `NEEDS_LLM` — and MUST NOT route a pair to inference that a deterministic rule already decides. A title match alone MUST NOT yield `AUTO_ACCEPT`, because distinct works commonly share a title. The default engine MUST be `heuristic`, which MUST complete a scan without contacting an inference service.

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

### Requirement: LLM-Assisted Duplicate Analysis and Scoring

The duplicate detection service MUST be able to evaluate candidate pairs using a local LLM (via Ollama API) to analyze semantic identity, determine a confidence score between 0.0 and 1.0, and provide a structured explanation rationale, but MUST NOT require inference to detect duplicates. Inference MUST be engaged only when the caller selects the `llama` engine, and MUST then apply only to pairs the deterministic classifier marked `NEEDS_LLM`. If the Ollama service is unreachable or returns an error, the system MUST log a diagnostic warning, record the failure, and avoid interrupting catalog operations. Because model latency on the reference hardware exceeds the configured client timeout, the system MUST NOT present the synchronous inference path as a supported way to complete a scan.

#### Scenario: Successful LLM candidate evaluation

- **WHEN** the caller selects the `llama` engine and the duplicate detection service submits a `NEEDS_LLM` candidate pair of Works with metadata to Ollama
- **THEN** the LLM returns a similarity evaluation containing a numeric confidence score, match verdict, and textual rationale.

#### Scenario: Ollama service unavailable during detection run

- **WHEN** the duplicate detection service attempts to evaluate a candidate pair while Ollama is unreachable
- **THEN** the system records an evaluation failure error, continues processing remaining candidates, and leaves the candidate status pending without crashing.

#### Scenario: Default scan engages no inference

- **WHEN** a scan runs under the default `heuristic` engine
- **THEN** the report states zero inference evaluations regardless of whether an inference service is reachable.

#### Scenario: Inference is confined to the undecided grey zone

- **WHEN** a scan runs under the `llama` engine
- **THEN** only pairs classified `NEEDS_LLM` are submitted for evaluation, and pairs decided `AUTO_ACCEPT` or `AUTO_REJECT` are not.

### Requirement: Duplicate Candidate Persistence and Lifecycle Management

The system MUST persist detected duplicate candidate pairs in a database table with attributes including source entity ID, target entity ID, entity tier (`work` or `manifestation`), a nullable confidence score, a `resolution_source` recording which stage decided the pair (`heuristic` or `llama`), LLM reasoning rationale, detection timestamp, and review status (`pending`, `merged`, `dismissed`). A candidate decided by the deterministic classifier MUST have a NULL confidence, because a rule verdict is categorical rather than probabilistic and MUST NOT be stored as a probability. A candidate decided by inference MUST carry a non-NULL confidence in the 0.0–1.0 range together with its rationale. An existing row predating the `resolution_source` column MUST be backfilled from the presence of an LLM rationale.

#### Scenario: Storing newly detected duplicate candidate

- **WHEN** the detection process queues a candidate pair, whether from inference scoring or from a deterministic rule
- **THEN** the system creates a `DuplicateCandidate` record with `pending` status and records the deciding stage in `resolution_source`.

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

The system MUST provide authenticated REST endpoints under `/api/v1/admin/duplicates` allowing authorized users to list candidates with pagination and filtering by entity tier or status, dismiss false positive candidates, execute merges, and trigger manual detection scans. Access MUST be authorized by permission rather than by role: listing requires `read:metadata`, while scanning, dismissing, and merging require `write:metadata`. An authenticated user holding only `read:metadata` MUST be able to inspect the queue and MUST NOT be able to mutate it. The system MUST rate-limit merge requests to bound the cost of a merge storm.

#### Scenario: Administrator retrieves pending duplicate candidates

- **WHEN** an authenticated user holding `read:metadata` sends a GET request to `/api/v1/admin/duplicates?status=pending`
- **THEN** the server returns a paginated list of candidate pairs with their entity metadata, confidence (nullable), `resolution_source`, and LLM reasoning.

#### Scenario: Non-admin user denied access to duplicate management

- **WHEN** an unauthenticated user, or an authenticated user without `read:metadata`, requests `/api/v1/admin/duplicates`
- **THEN** the server rejects the request with HTTP 401 Unauthorized or HTTP 403 Forbidden.

#### Scenario: A read-only contributor cannot merge

- **WHEN** an authenticated user holding only `read:metadata` posts a merge to `/api/v1/admin/duplicates/<id>/merge`
- **THEN** the server rejects the request with HTTP 403 Forbidden and no entity is modified.

#### Scenario: Dismissing a false positive duplicate candidate

- **WHEN** a user holding `write:metadata` posts a dismissal request to `/api/v1/admin/duplicates/<id>/dismiss`
- **THEN** the system updates the candidate status to `dismissed` and records the dismissing user's identity.

#### Scenario: Excessive merge requests are rate limited

- **WHEN** a client exceeds the configured merge rate limit
- **THEN** the server responds with HTTP 429 Too Many Requests and performs no further merges.

### Requirement: Admin Duplicate Review Interface

The admin web interface MUST provide a dedicated Duplicate Review view at `/admin/duplicates` that displays pending candidate pairs side-by-side with entity metadata, cover images, hierarchy details (associated Expressions or Items), a badge labelled by the stage that decided the pair, and the reasoning, allowing administrators to select which entity to retain as primary and execute the merge or dismiss the candidate. The badge MUST distinguish a model verdict from a rule verdict: a model verdict MUST be shown as a labelled percentage, and a rule verdict MUST be shown as a match carrying no number, so a categorical verdict is never presented as a calibrated probability. The interface MUST NOT imply that running a scan requires a language model.

#### Scenario: Side-by-side candidate inspection

- **WHEN** an administrator navigates to `/admin/duplicates` and selects a pending candidate pair
- **THEN** the interface displays both entities side by side with titles, creators, FRBR hierarchy children, and the reasoning for the match.

#### Scenario: The decision badge names the stage that made it

- **WHEN** the review queue displays a candidate decided by the deterministic classifier and one decided by a language model
- **THEN** the rule verdict's badge carries no percentage, and the model verdict's badge is labelled as a model confidence.

#### Scenario: A candidate with no confidence does not render as zero percent

- **WHEN** the review queue displays a candidate whose confidence is NULL
- **THEN** the badge presents the pair as a match rather than as a `0%` match.

#### Scenario: Empty state does not imply inference is required

- **WHEN** an administrator opens the review queue with no pending candidates
- **THEN** the empty-state copy states that a scan can be resolved from the records alone and points to the `llama` engine for the remaining grey zone.

#### Scenario: Executing merge from administrative interface

- **WHEN** an administrator selects the primary entity and confirms the merge in the confirmation dialog
- **THEN** the UI submits the merge request, shows a progress indicator, displays a success toast upon completion, and removes the resolved candidate from the pending list.

#### Scenario: Destructive controls are hidden from viewers

- **WHEN** a user without `write:metadata` opens the review queue
- **THEN** the dismiss and merge controls are absent, while the side-by-side comparison remains available.

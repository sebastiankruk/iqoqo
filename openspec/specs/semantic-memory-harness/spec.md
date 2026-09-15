# semantic-memory-harness Specification

## Purpose

Defines operational, retrieval, security, and lifecycle requirements for developer and agent semantic memory services across iQoQo.

## Requirements

### Requirement: Deterministic Environment Path Resolution
The semantic memory harness SHALL resolve all CLI binaries using the repository virtual environment (`.venv/bin/`) or wrapper scripts rather than relying on ambient host PATH executables.

#### Scenario: Tool query execution in subshell

- **WHEN** an agent or developer executes a knowledge query via Makefile target or documented CLI snippet
- **THEN** the command resolves `.venv/bin/graphify`, `.venv/bin/mempalace`, or `.venv/bin/mykg` directly without failing with exit code 127 (`command not found`).

### Requirement: Session-Agnostic myKG Query Target
The myKG interface SHALL provide a unified query mechanism that automatically identifies and queries the latest session directory without requiring manual discovery of timestamped directories.

#### Scenario: Querying myKG knowledge graph

- **WHEN** an agent or developer executes `make mykg-ask Q="<question>"`
- **THEN** the harness automatically resolves the most recent session directory in `mykg_sessions/` and runs the query against it.

#### Scenario: Querying when no session exists

- **WHEN** a query is executed and no valid session directory is found in `mykg_sessions/`
- **THEN** the system reports a clear diagnostic message directing the user to run an index build first.

### Requirement: MemPalace Query Sanitization and Output Preservation
The MemPalace retrieval interface SHALL preserve complete query output and diagnostics, and the ingestion pipeline SHALL sanitize credentials and local developer paths before vector storage.

#### Scenario: Searching MemPalace memory

- **WHEN** an agent queries MemPalace for architectural or conversational memory
- **THEN** query execution preserves all output chunks and diagnostics without truncation via head pipes or suppression of standard error.

#### Scenario: Sanitizing notes and configuration during ingestion

- **WHEN** MemPalace mines project documents, operational notes, and configuration files
- **THEN** plaintext secrets (e.g. passwords, API tokens) and absolute local host paths are redacted before generating embeddings.

### Requirement: CodeGraph First-Stop Navigation Protocol
The developer tooling directives SHALL designate CodeGraph as the mandatory AST symbol navigation tool prior to falling back to broad text grep scans.

#### Scenario: Locating code symbol definitions and callers

- **WHEN** an agent investigates a class, function, database model, or route symbol
- **THEN** the agent executes `codegraph node`, `codegraph callers`, or `codegraph impact` before attempting broad text-based grep scans.

### Requirement: Decoupled Knowledge Synchronization Lifecycle
The build orchestration system SHALL strictly separate fast, sub-minute local indexing from multi-minute or token-consuming batch operations.

#### Scenario: Routine developer or agent sync

- **WHEN** a developer or agent runs routine knowledge synchronization (`make knowledge-sync`)
- **THEN** the system updates only CodeGraph and Graphify in parallel, completing in under 60 seconds without executing MemPalace full hallway indexing or launching the myKG Docker daemon.

#### Scenario: Prohibition on automated full sync during interactive sessions

- **WHEN** an agent completes a development session or runs automated post-task hooks
- **THEN** the agent and tooling directives SHALL NOT invoke `make knowledge-sync-full` or full `make mempalace-index`.

#### Scenario: Targeted single-file memory update during interactive sessions

- **WHEN** an agent modifies a specific domain document or code file and needs to update MemPalace memory
- **THEN** the agent runs surgical single-file mining (`mempalace mine <file> --wing iqoqo`) without triggering a full palace rebuild.

#### Scenario: Scheduled or release synchronization

- **WHEN** a release build or explicit full knowledge extraction is initiated (`make knowledge-sync-full`)
- **THEN** the system triggers MemPalace full index and myKG update to regenerate the complete ontological ABox/TBox vault and associative hallway graph.

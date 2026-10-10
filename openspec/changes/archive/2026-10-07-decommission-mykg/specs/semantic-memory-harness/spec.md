## MODIFIED Requirements

### Requirement: Deterministic Environment Path Resolution

The semantic memory harness SHALL resolve all CLI binaries using the repository virtual environment (`.venv/bin/`) or wrapper scripts rather than relying on ambient host PATH executables.

#### Scenario: Tool query execution in subshell

- **WHEN** an agent or developer executes a knowledge query via Makefile target or documented CLI snippet
- **THEN** the command resolves `.venv/bin/graphify` or `.venv/bin/mempalace` directly without failing with exit code 127 (`command not found`).

### Requirement: Decoupled Knowledge Synchronization Lifecycle

The build orchestration system SHALL strictly separate fast, sub-minute local indexing from multi-minute batch operations.

#### Scenario: Routine developer or agent sync

- **WHEN** a developer or agent runs routine knowledge synchronization (`make knowledge-sync`)
- **THEN** the system updates only CodeGraph and Graphify in parallel, completing in under 60 seconds without executing MemPalace full hallway indexing.

#### Scenario: Prohibition on automated full sync during interactive sessions

- **WHEN** an agent completes a development session or runs automated post-task hooks
- **THEN** the agent and tooling directives SHALL NOT invoke `make knowledge-sync-full` or full `make mempalace-index`.

#### Scenario: Targeted single-file memory update during interactive sessions

- **WHEN** an agent modifies a specific domain document or code file and needs to update MemPalace memory
- **THEN** the agent runs surgical single-file mining (`mempalace mine <file> --wing iqoqo`) without triggering a full palace rebuild.

#### Scenario: Scheduled or release synchronization

- **WHEN** a release build or explicit full knowledge extraction is initiated (`make knowledge-sync-full`)
- **THEN** the system triggers a MemPalace full index to regenerate the associative hallway graph.

## REMOVED Requirements

### Requirement: Session-Agnostic myKG Query Target

**Reason**: myKG is decommissioned in v0.8.3. The RDF/Turtle knowledge graph it compiled duplicated ontology knowledge already exposed as RDF/JSON-LD by the application and already indexed for navigation by MemPalace and Graphify, at a cost of ~US$4.36 and 15–60 minutes per full run. The `make mykg-ask` target, the `mykg_sessions/` store it read, and the `iqoqo-mykg` skill that wrapped it are all removed.

**Migration**: Use the application's own SPARQL/RDF endpoints or the `openspec/specs/` ontology for formal FRBR domain queries, and `mempalace search` / `graphify query` for developer memory and architecture navigation. There is no replacement batch compiler; no graph is regenerated.

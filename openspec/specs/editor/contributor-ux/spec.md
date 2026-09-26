# editor/contributor-ux Specification

## Purpose

Provides a structured, form-based contributor management interface in the FRBR catalog editor with entity-scoped role selection, multi-word name capitalization, and bidirectional synchronization with FRBRoo event models.

## Requirements

### Requirement: Structured Contributor Form Rows
The FRBR Editor SHALL render dedicated, structured form rows for managing contributors on Work, Expression, and Manifestation entities instead of unstructured JSON textareas or stringified metadata inputs. Each row SHALL contain a controlled Role selector and an Agent Name text input.

#### Scenario: Displaying existing contributors on editor load

- **WHEN** an operator opens the FRBR editor for an entity that has associated contributors
- **THEN** the editor SHALL render a structured row for each contributor populated with their assigned role and formatted agent name

#### Scenario: Adding a new contributor row

- **WHEN** an operator clicks the action to add a contributor
- **THEN** the editor SHALL append a new empty contributor row containing a default role selection and an empty agent name input

#### Scenario: Removing an existing contributor row

- **WHEN** an operator clicks the remove action on a specific contributor row
- **THEN** the editor SHALL delete that row from the active form state and retain the remaining contributor rows in their display sequence

#### Scenario: Reordering contributor display sequence

- **WHEN** multiple contributors are defined for the same entity
- **THEN** the system SHALL preserve and submit the visual sequence order of the contributors for display prioritization

### Requirement: Entity-Scoped Role Vocabulary
The Role selector SHALL dynamically populate available roles matching the FRBRoo event semantics of the active entity level, preventing cross-level ontological mismatches.

#### Scenario: Selecting Work creative roles

- **WHEN** editing contributors on a Work entity (Composition Event)
- **THEN** the role selector SHALL only offer creative roles (such as author, composer, lyricist, director, writer, or designer)

#### Scenario: Selecting Expression performance roles

- **WHEN** editing contributors on an Expression entity (Performance Event)
- **THEN** the role selector SHALL only offer realization and performance roles (such as performer, conductor, narrator, actor, ensemble, or translator)

#### Scenario: Selecting Manifestation publication roles

- **WHEN** editing contributors on a Manifestation entity (Publication Event)
- **THEN** the role selector SHALL only offer publication roles (such as publisher, studio, distributor, or manufacturer)

### Requirement: Intelligent Multi-Word Name Capitalization
The system SHALL normalize and capitalize contributor names, correctly processing multi-word names, hyphenated names, initials, and language-specific surname particles.

#### Scenario: Capitalizing standard multi-word names

- **WHEN** an operator enters a lowercase multi-word name such as "gabriel garcia marquez"
- **THEN** the system SHALL format the name to Title Case as "Gabriel Garcia Marquez"

#### Scenario: Preserving cultural surname particles

- **WHEN** an operator enters a name containing recognized surname particles such as "ludwig van beethoven", "ursula k. le guin", or "leonardo da vinci"
- **THEN** the system SHALL capitalize the given names while keeping interior particles lowercase ("Ludwig van Beethoven", "Ursula K. Le Guin", "Leonardo da Vinci")

#### Scenario: Capitalizing hyphenated names and initials

- **WHEN** an operator enters a hyphenated name or name with initials such as "jean-luc godard" or "j. r. r. tolkien"
- **THEN** the system SHALL capitalize both segments of the hyphenated name ("Jean-Luc Godard") and each punctuated initial ("J.R.R. Tolkien")

#### Scenario: Sanitizing redundant whitespace

- **WHEN** an operator enters a name with leading, trailing, or multiple consecutive internal spaces
- **THEN** the system SHALL collapse consecutive spaces to a single space and strip leading and trailing whitespace

### Requirement: Structured Agent Parsing and Persistence
The backend SHALL parse structured contributor payloads during FRBR entity creation or modification, resolving or creating Contributor entities and establishing the appropriate event relationships.

#### Scenario: Persisting valid contributor list on entity update

- **WHEN** an operator saves an entity with a list of structured contributor objects containing valid role and name attributes
- **THEN** the system SHALL normalize each name, get or create the corresponding Contributor record, and synchronize the entity's contribution links

#### Scenario: Backward-compatible parsing of legacy metadata

- **WHEN** an entity update payload contains legacy contributor metadata (such as an array of author strings in `meta`)
- **THEN** the backend SHALL parse the legacy entries, normalize their names, and map them to standard contributor records without data loss

#### Scenario: Validating empty or malformed contributor entries

- **WHEN** an entity update is submitted with contributor entries missing a name or containing only whitespace
- **THEN** the system SHALL filter out the empty entries before persisting, or reject the update if mandatory fields are invalid

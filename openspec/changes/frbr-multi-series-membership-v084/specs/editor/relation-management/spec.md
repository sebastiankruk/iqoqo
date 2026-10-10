## ADDED Requirements

### Requirement: Multi-Series Work Membership Management
The system SHALL support associating a single Work with multiple series containers, preserving separate ordinal sequence positions and series labels for each membership.

#### Scenario: Assigning a Work to multiple series containers
- **WHEN** an authorized custodian adds a Work to a second series container (e.g. adding a novel to both "Cosmere" and "Mistborn")
- **THEN** the system creates distinct membership records with independent sequence numbers without detaching previous series associations.

#### Scenario: Visualizing multi-series badges in catalog views
- **WHEN** a user views a Work or an Item belonging to multiple series
- **THEN** the interface displays visual badges for each active series, indicating the series title and the title's sequence number within that series.

#### Scenario: Removing one series membership without affecting others
- **WHEN** a custodian removes a Work from one specific series container
- **THEN** that specific membership is removed while all other series affiliations and sequences remain intact.

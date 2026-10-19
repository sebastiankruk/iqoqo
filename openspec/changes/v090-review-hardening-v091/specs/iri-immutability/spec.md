## ADDED Requirements

### Requirement: Chained Multi-Hop Tombstone Resolution
The system SHALL recursively resolve chained `owl:sameAs` and ActivityStreams `Move` tombstones so that querying any historical entity URI points directly to the ultimate surviving canonical entity.

#### Scenario: Chained merge resolves to final target
- **WHEN** Entity A is merged into Entity B, and Entity B is subsequently merged into Entity C
- **THEN** dereferencing Entity A returns a 301/410 redirect referencing Entity C.

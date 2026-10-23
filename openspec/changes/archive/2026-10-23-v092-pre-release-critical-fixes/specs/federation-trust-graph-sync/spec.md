## ADDED Requirements

### Requirement: Thread-Safe Periodic Instance Health Probing
The system SHALL execute only stateless HTTP NodeInfo/root discovery requests inside `ThreadPoolExecutor` worker threads in `probe_registered_instances`, and SHALL apply all SQLAlchemy ORM attribute mutations and `db.session.commit()` calls on the main calling thread.

#### Scenario: Concurrent health probe updates instance metadata safely
- **WHEN** `probe_registered_instances` probes multiple non-blocked `FederationInstance` records concurrently
- **THEN** worker threads perform HTTP requests without accessing `db.session`, and the main thread persists `last_seen_at`, `software_name`, `software_version`, and `shared_inbox_url` in a single thread-safe commit

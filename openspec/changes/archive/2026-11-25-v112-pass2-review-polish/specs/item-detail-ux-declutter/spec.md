## ADDED Requirements

### Requirement: Synchronous Cover Upload Fallback Disables In-Request LLM Generation

When `POST /api/manifestations/<id>/cover/upload` falls back to synchronous `process_cover_pipeline()` execution because Celery/Valkey task dispatch returns `None`, it MUST pass `llm_permissions={}` (explicitly overriding any user-level LLM cover permissions) so that a corrupted or failed Tier-1 user photo never cascades into synchronous LLM cover generation inside the HTTP request worker.

#### Scenario: Synchronous cover upload fallback passes empty llm_permissions even for LLM-permitted users

- **GIVEN** an authenticated user holding LLM cover generation permissions and a Valkey/Celery outage where `start_cover_processing()` returns `None`
- **WHEN** the user uploads a cover image via `POST /api/manifestations/<id>/cover/upload`
- **THEN** `process_cover_pipeline()` is invoked synchronously with `llm_permissions={}` and returns HTTP `200` without invoking any external LLM cover provider

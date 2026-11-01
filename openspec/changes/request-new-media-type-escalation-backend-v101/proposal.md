## Why
In `iqoqo development notes.md`, collectors requested *"requesting new type #v100"*. Because **iqoqo** enforces a strict, ontologically validated taxonomy (`shared/format_mappings.yaml` and `docs/ontology/iqoqo.ttl`), allowing arbitrary unvalidated free-text formats directly into the database would corrupt faceted navigation and Linked Open Data graphs. Instead, we need a structured backend escalation workflow where collectors can propose a new media category or physical format to Custodians/Admins.

## What Changes

- **Extend `EscalationRequest` for Entity-Less `new_media_type` Proposals (`app/db/social.py`, `app/api/social.py`):** Allow `EscalationRequest` to be created with `request_type="new_media_type"` and nullable `manifestation_id` / `work_id`, storing a validated Pydantic structured payload (`proposed_category`, `proposed_format`, `parent_frbr_class`: `"F1_Work" | "F16_Container_Work"`, `sample_identifier_or_url`, `suggested_properties`, `rationale`).
- **Custodian Notification & Resolution Hook (`app/api/social.py`):** Emit an in-app notification (`social.notifications`) to Custodians/Admins when a `new_media_type` request is submitted, and notify the requesting collector when the proposal is approved, deferred, or rejected with custodian notes.

## Capabilities

### New Capabilities
- `new-media-type-escalation-backend`: Backend API and database support for submitting, listing, and resolving structured `new_media_type` ontology/taxonomy proposals via the Custodian escalation system.

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

- `app/db/social.py`, `migrations/versions/*_v1_0_1_escalation_nullable_entity.py` (if `manifestation_id` requires nullable constraint update)
- `app/api/social.py`, `app/schemas/social.py` (or Pydantic validation in `social.py`)
- `tests/test_new_media_type_requests.py`

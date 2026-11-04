## 1. Schema & Backend API for `new_media_type` Escalations (`app/`)

- [ ] 1.1 Update `EscalationRequest` in `app/db/social.py` (and generate a linear Alembic migration if `manifestation_id` is currently `nullable=False`) to permit `manifestation_id=None` when `request_type == "new_media_type"`.
- [ ] 1.2 Add Pydantic validation for `new_media_type` escalation payloads (`proposed_category`, `proposed_format`, `parent_frbr_class`, `sample_identifier_or_url`, `rationale`) in `app/api/social.py`.
- [ ] 1.3 Wire `new_media_type` submission and custodian resolution into `social.notifications` so custodians receive alerts and requesters are notified when their type request is triaged.

## 2. Verification & Tests

- [ ] 2.1 Author backend tests in `tests/test_new_media_type_requests.py` verifying creation, validation, pagination, custodian resolution, and notification emission for `new_media_type` requests.
- [ ] 2.2 Run `IQOQO_AI_MODE=1 make lint` and `IQOQO_AI_MODE=1 make test`.

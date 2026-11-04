## 1. `<RequestNewTypeModal />` & Custodian Triage UI (`frontend/`)

- [ ] 1.1 Create `frontend/components/social/request-new-type-modal.tsx` using Shadcn `Dialog`, `Select`, `Input`, and `Textarea` to submit `request_type="new_media_type"` payloads.
- [ ] 1.2 Mount the `"Request new media type"` trigger in the `/scan` manual-entry fallback (passing any scanned barcode as `defaultSampleIdentifier`) and on `/feedback`.
- [ ] 1.3 Update `frontend/components/admin/escalation-queue.tsx` to render `new_media_type` requests (where `manifestation_id` is `null`) with structured proposal fields and custodian Approve/Reject actions.
- [ ] 1.4 Add `en.json` and `pl.json` (sentence-case Polish) translation keys.

## 2. Verification & Tests

- [ ] 2.1 Author unit tests in `frontend/__tests__/components/social/request-new-type-modal.test.tsx` and update `escalation-queue` tests.
- [ ] 2.2 Run `IQOQO_AI_MODE=1 make lint` and `IQOQO_AI_MODE=1 make test`.

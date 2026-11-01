## 1. Backend Peering Directionality Signal & Frontend Matrix

- [ ] 1.1 Extend `FederationInstance` serialization in `app/api/admin.py` to include `peering_direction` (`"reciprocal" | "outbound_only" | "inbound_only" | "blocked"`) and `effective_capabilities` summary (`auto_metadata_sync`, `custodian_merge_queue`, `friend_follows`, `cross_instance_loans`).
- [ ] 1.2 Update `frontend/components/admin/federation-instances.tsx` to display the Peering Directionality badge and an expandable/tooltip Capabilities Matrix explaining unilateral vs. bilateral behavior.
- [ ] 1.3 Update the in-app Federation guide in `/help` and add `en.json` / `pl.json` (sentence-case Polish) translations.

## 2. Verification & Tests

- [ ] 2.1 Author unit tests in `tests/test_federation_discovery_admin.py` and `frontend/__tests__/components/admin/federation-instances.test.tsx` verifying unilateral vs. reciprocal badges and capabilities matrix rendering.
- [ ] 2.2 Run `IQOQO_AI_MODE=1 make lint` and `IQOQO_AI_MODE=1 make test`.

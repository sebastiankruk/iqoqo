# Tasks: v094-pre-merge-bug-hardening-v094

- [x] Scope inbound follow activities by pending actor URIs and local target user in `friend_service.py` (M1)
- [x] Implement outbound ActivityPub `Reject(Follow)` and `Undo(Follow)` dispatch in `friend_service.py` (M2)
- [x] Sanitize WebFinger SQL queries and fix domain fallback parameter appending (M3)
- [x] Enforce anchored actor IRI checks in `federation_handlers.py` and hide notification actions for accepted status in `notification-center.tsx` (M4)
- [x] Update E2E test placeholders in `federation_pair_live.spec.ts` and `federation_matrix_workflows.spec.ts` (M5)
- [x] Clean up and verify orphaned folders in `openspec/changes/` (M6)
- [x] Add domain normalization, keypair idempotency, and consent preservation in `friend_service.py` and `profile.py` (L1)
- [x] Add database rollback on key sync failure in `federation_keys.py` (L2)
- [x] Add migration downgrade row normalization in `v0_9_4_user_friends_only_checks.py` and harden `restore.sh` (L3)
- [x] Update `docs/FEDERATION.md` peering table and stamp `docs/CHANGELOG.md` (L4)
- [x] Run test suites, linters, and secret scans to verify all checks pass

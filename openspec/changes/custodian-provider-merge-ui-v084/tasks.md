## 1. Backend Selective Merge API

- [ ] 1.1 Implement `POST /api/v1/admin/frbr/manifestation/<id>/provider-merge` in `app/api/admin.py` with `@require_permission(WRITE_METADATA)`; verify endpoint authorization
- [ ] 1.2 Implement atomic multi-tier update handler in `app/core/frbr_service.py` applying selected field attributes, updating `meta["_provenance"]`, and writing to `EntityAuditLog`; verify transactional integrity with pytest
- [ ] 1.3 Add pytest cases verifying selective merge across Work (authors/title) and Manifestation (cover/publisher) tiers

## 2. Frontend Custodian UI & Verification

- [ ] 2.1 Create `frontend/components/admin/provider-merge-dialog.tsx` displaying provider fragments grouped by Work, Expression, and Manifestation tiers; verify component rendering
- [ ] 2.2 Wire "Merge Provider Metadata" trigger in `frontend/components/admin/frbr-editor.tsx` action menu; verify modal launch
- [ ] 2.3 Add Vitest tests for `provider-merge-dialog.tsx` testing field selection, payload generation, and successful mutation toast feedback

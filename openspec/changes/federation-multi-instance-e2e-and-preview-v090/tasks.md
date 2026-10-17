## 1. Test Harness Implementation

- [ ] 1.1 Create `frontend/__tests__/e2e/federation_multi_instance.spec.ts` testing WebFinger resolution and cross-instance interaction across dual browser contexts
- [ ] 1.2 Add helper scripts to launch secondary local test backend during multi-instance test runs

## 2. Orchestration & Preview Staging

- [ ] 2.1 Add `docker-compose.federation-preview.yml` definition for secondary peer instance
- [ ] 2.2 Add `FEDERATION_PAIR` parameter to `make preview-up` and integrate into `iqopretest` pre-flight options
- [ ] 2.3 Document dual-instance manual inspection steps in `docs/TESTING.md`

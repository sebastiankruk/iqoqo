## 1. Store Privacy Manifests & Optional Fastlane Signing

- [ ] 1.1 Create `frontend/ios/App/App/PrivacyInfo.xcprivacy` declaring `NSPrivacyTracking = false` and `NSPrivacyAccessedAPITypeUserDefaults` (`CA92.1`).
- [ ] 1.2 Add optional secret-gated release signing steps to `.github/workflows/mobile-build.yml` and document store submission procedures in `docs/STORE_SUBMISSION.md`.

## 2. Multi-Agent `v1.0.x` LTS Audit & Documentation Gate

- [ ] 2.1 Execute Security, SRE, QA, Ontologist, UX, and TechComm review sweep across all `v1.0.0`–`v1.0.2` changes (`C95`–`C109`) and remediate any findings.
- [ ] 2.2 Verify `scripts/sync_ontology.py --check`, OpenAPI 3.1 contract tests, `IQOQO_AI_MODE=1 make secret-scan`, `IQOQO_AI_MODE=1 make lint`, and `IQOQO_AI_MODE=1 make test`, and finalize `docs/CHANGELOG.md`.

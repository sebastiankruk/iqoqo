## Why
To finalize the `v1.0.x` release stream as a long-term support (LTS) baseline and prepare for optional Apple App Store (TestFlight) and Google Play Console submissions, we need Apple's mandatory iOS 17+ `PrivacyInfo.xcprivacy` manifest, Google Play Data Safety declarations (asserting 100% zero corporate tracking/telemetry), optional Fastlane release signing lanes, and a comprehensive multi-agent `1.0.x` security/architecture audit gate.

## What Changes

- **Apple `PrivacyInfo.xcprivacy` & Google Play Data Safety Manifests:** Add `frontend/ios/App/App/PrivacyInfo.xcprivacy` declaring required-reason APIs (`UserDefaults` / `CA92.1` for `@capacitor/preferences`) and `NSPrivacyTracking = false`, plus `docs/STORE_SUBMISSION.md` with Google Play Data Safety answers and store listing metadata.
- **Optional Fastlane Store Signing Lanes (`.github/workflows/mobile-build.yml`):** Add conditional Fastlane / signed release steps in `.github/workflows/mobile-build.yml` that remain skipped when store secrets (`APPLE_CERTIFICATE_P12`, `ANDROID_KEYSTORE_BASE64`) are absent (preserving zero-account sideload builds) and automatically sign/upload when configured.
- **Full `v1.0.x` Multi-Agent LTS Audit Gate:** Execute Security, SRE, QA, Ontologist, UX, and TechComm review across `C95`–`C109`, update `docs/CHANGELOG.md` and `docs/MOBILE.md`, and verify 100% OpenAPI 3.1 + SHACL ontology compliance.

## Capabilities

### New Capabilities
- `v10x-store-manifests-and-lts-gate`: iOS `PrivacyInfo.xcprivacy` zero-tracking manifest, optional signed store CI lanes, and the `v1.0.x` multi-agent LTS release audit gate.

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

- `frontend/ios/App/App/PrivacyInfo.xcprivacy`
- `.github/workflows/mobile-build.yml`
- `docs/STORE_SUBMISSION.md`, `docs/CHANGELOG.md`
- `tests/test_infra_config.py`

## Purpose
Provide Apple/Google privacy nutrition manifests (`PrivacyInfo.xcprivacy`), optional secret-gated store signing in CI, and the final `v1.0.x` multi-agent LTS release audit gate.

## ADDED Requirements

### Requirement: Zero-Tracking iOS Privacy Manifest & Secret-Gated Store CI

The iOS project SHALL include `frontend/ios/App/App/PrivacyInfo.xcprivacy` with `NSPrivacyTracking` set to `false`, and `.github/workflows/mobile-build.yml` SHALL keep sideload artifacts enabled by default while gating signed store uploads on optional signing secrets.

#### Scenario: Inspecting iOS privacy manifest and CI workflow
- **GIVEN** `frontend/ios/App/App/PrivacyInfo.xcprivacy` and `.github/workflows/mobile-build.yml`
- **WHEN** `tests/test_infra_config.py` validates the mobile configuration
- **THEN** `NSPrivacyTracking` is `false`, `CA92.1` is declared for `UserDefaults`, and unsigned sideload jobs run without requiring store secrets.

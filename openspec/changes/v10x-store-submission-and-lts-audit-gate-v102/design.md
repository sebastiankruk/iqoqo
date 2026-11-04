## Context

Mirroring `C90` (`v09x-final-review-and-mobile-readiness-gate-v094`), `C110` closes out the `1.0.x` stream with store privacy manifests, optional store signing automation, and a full multi-agent security/ontology/UX audit before `v1++` (Magic Shelf Scan AI & MCP server).

## Goals / Non-Goals

**Goals:**
- Provide `frontend/ios/App/App/PrivacyInfo.xcprivacy` (`NSPrivacyTracking = false`) and `docs/STORE_SUBMISSION.md`.
- Keep `.github/workflows/mobile-build.yml` sideload-first by default while supporting optional signed TestFlight / Play Store uploads when secrets are configured.
- Pass the full `1.0.x` multi-agent review gate with zero critical/moderate debt.

**Non-Goals:**
- Requiring paid developer accounts to run standard CI builds.

## Decisions

### Conditional Store Signing Guarded by Repository Secrets
* **Decision:** Gate signed release steps in `.github/workflows/mobile-build.yml` behind `if: env.ANDROID_KEYSTORE_BASE64 != ''` and `if: env.APPLE_CERTIFICATE_P12 != ''` so unsigned sideload builds (`C99`) always succeed without paid store credentials.
* **Rationale:** Supports free sideloading indefinitely while making store publication a zero-code-change secret toggle when ready.

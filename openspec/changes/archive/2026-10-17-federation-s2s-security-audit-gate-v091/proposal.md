## Why
Acts as the strict stabilization gate for Milestone v0.9.1 before shipping server-to-server federation capabilities to production.
## What Changes

- Implement two-instance E2E simulation harness in `tests/test_federation_e2e.py`.
- Verify SSRF defenses against DNS rebinding, internal subnets, and HTTP redirect chains.
- Verify rejection of tampered Digest headers, expired Date headers, and keyId domain mismatches.
- Verify OpenObserve metrics `federation_sig_failures_total` and `federation_delivery_failures_total`.

## Capabilities

### New Capabilities
- `federation-security-audit`: Two-instance E2E simulation harness, SSRF chaos testing, signature replay protection, and OpenObserve telemetry verification

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

Verification and testing gate across backend and SRE observability.

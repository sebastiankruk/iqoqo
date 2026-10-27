## MODIFIED Requirements

### Requirement: Manual Federation Preview Staging Option
The deployment orchestration scripts MUST provide an option to initialize a dual-instance federation preview stack for manual validation that preserves peer cryptographic keys across restarts, enforces secure production-parity defaults (`FEDERATION_AUTO_ACCEPT_FOLLOWS=false`), cleans up synthetic internal smoke-test trust records after preflight checks, and documents full administrative peering and key-pinning procedures.

#### Scenario: Operator boots dual-instance preview stack

- **WHEN** an operator runs `make preview-up FEDERATION_PAIR=1` or triggers the federation preview profile in `iqopretest`
- **THEN** two isolated application stacks (primary and peer) are provisioned with interconnected internal networking, persistent cryptographic key volumes, and mutual seed credentials
- **THEN** the operator can open both instances in a browser to inspect federation activity logs and UI reactions in real time

#### Scenario: Preflight verification script leaves zero synthetic internal trusted peers behind

- **WHEN** `scripts/verify_federation_preview.sh` executes internal container-to-container discovery smoke checks (`web:5000` and `peer-web:5000`)
- **THEN** a `try ... finally` cleanup block restores prior state and removes synthetic `web:5000` / `peer-web:5000` records before exiting so persistent preview databases are never polluted with pre-trusted internal hostnames

#### Scenario: Manual federation walkthrough documents settings, defaults, and SHA-256 fingerprint verification

- **WHEN** an operator or QA engineer follows `.context/notes/tests/federation-manual-testing-walkthrough.md`
- **THEN** the guide documents `Auto-Accept Follow Requests` (default `Disabled`), `Default Peer Trust` (`untrusted` / `pending`), `Instance Actor Key Fingerprint` out-of-band SHA-256 verification, and clean public-domain peering (`preview.iqoqo.cc` <-> `peer.iqoqo.cc`)

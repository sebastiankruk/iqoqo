# federation-multi-instance-e2e Specification

## Purpose
Defines automated multi-instance end-to-end integration testing and orchestration capabilities for iqoqo federation, validating ActivityPub WebFinger discovery, dual-context identity isolation, signed Follow activity delivery, and reproducible local multi-instance preview environments.

## Requirements

### Requirement: Multi-Instance E2E Playwright Federation Suite
The testing pipeline MUST support executing Playwright E2E tests simulating interactions across two distinct iqoqo instance configurations (Instance A and Instance B) with isolated databases, domain origins, and cryptographic identities.

#### Scenario: Cross-instance Actor discovery and Follow interaction in E2E

- **GIVEN** two local test instances running at distinct origins (e.g. `http://localhost:3000` and `http://localhost:3001`)
- **WHEN** a user on Instance A searches for `@alice@localhost:3001`
- **THEN** Instance A resolves WebFinger and fetches Alice's Actor JSON-LD representation
- **WHEN** the user on Instance A clicks "Follow"
- **THEN** a signed ActivityPub `Follow` activity is delivered to Instance B's inbox and processed

### Requirement: Manual Federation Preview Staging Option
The deployment orchestration scripts MUST provide an option to initialize a dual-instance federation preview stack for manual validation.

#### Scenario: Operator boots dual-instance preview stack

- **WHEN** an operator runs `make preview-up FEDERATION_PAIR=1` or triggers the federation preview profile in `iqopretest`
- **THEN** two isolated application stacks (primary and peer) are provisioned with interconnected internal networking and mutual seed credentials
- **THEN** the operator can open both instances in a browser to inspect federation activity logs and UI reactions in real time

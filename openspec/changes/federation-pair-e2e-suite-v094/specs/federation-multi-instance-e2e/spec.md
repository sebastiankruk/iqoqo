## ADDED Requirements

### Requirement: Automated Dual-Origin Live Federation Click-Through Suite
The Playwright E2E testing framework MUST execute a multi-instance federation test suite against two concurrently running live application origins without mock route interceptions, asserting full cross-instance user journeys through accessible UI interactions.

#### Scenario: Cross-instance trust peering and user consent via UI
- **WHEN** an administrator opens the Trust Graph dashboard on Instance A and registers Instance B as a trusted peer
- **AND** a user on Instance B toggles federation consent on their profile page
- **THEN** both instances record mutual peering state and permit cross-instance ActivityPub discovery

#### Scenario: Dual-origin social follow and notification handshake
- **WHEN** a user on Instance A navigates to the social discovery interface and submits a follow request targeting a user on Instance B
- **THEN** a signed ActivityPub `as:Follow` activity is delivered across the network boundary to Instance B
- **AND** the user on Instance B observes an incoming notification badge and follow request in the Notification Center
- **AND** approving or auto-accepting the follow returns a signed `as:Accept` activity, rendering both users as accepted friends

#### Scenario: Cross-instance physical loan request and custody transfer
- **WHEN** an accepted friend on Instance A browses the connected library directory to view Instance B's public holdings
- **AND** submits an in-app loan request for a lendable item owned by Instance B
- **THEN** Instance B receives a pending loan request with federated origin metadata
- **WHEN** the item owner on Instance B approves the request in the lending administration interface
- **THEN** the item collection status updates to `lent`
- **AND** an immutable `ItemCustodyEvent` (`crm:E10_Transfer_of_Custody`) is recorded in Instance B's custody ledger
- **AND** Instance A receives an ActivityPub `as:Accept` activity and displays an approval notification to the borrower

#### Scenario: Cross-instance item return and custody reconciliation
- **WHEN** the item owner on Instance B marks the lent item as returned in the lending interface
- **THEN** the item collection status resets to `available`
- **AND** a return custody event is recorded in the immutable custody ledger

### Requirement: Standardized Federation Pair CI Test Runner
The build and test orchestration system MUST provide automated Makefile and continuous integration targets that boot an isolated dual-instance paired stack, perform automated preflight connectivity probes, execute the dual-origin Playwright suite, and cleanly tear down resources.

#### Scenario: Automated CI execution of federation pair tests
- **WHEN** the continuous integration runner triggers `make test-e2e-federation`
- **THEN** the system boots isolated primary and secondary container stacks with distinct databases and ports
- **AND** verifies HTTP health and WebFinger endpoints before running Playwright
- **AND** executes the dual-origin live federation suite
- **AND** terminates all test containers upon completion, archiving logs and test traces on failure

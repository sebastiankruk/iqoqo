## ADDED Requirements

### Requirement: E2E screenshot wait state stability
Playwright E2E tests in `ux_audit.spec.ts` SHALL use `networkidle` wait state for screenshots instead of `domcontentloaded`, and SHALL intercept image network requests (`**/*.jpg`) with mock image buffers to prevent external network flakiness.

#### Scenario: Screenshot captures fully rendered page
- **WHEN** a Playwright test takes a screenshot for visual regression
- **THEN** the page SHALL be fully hydrated with all async API calls resolved and lazy images painted

### Requirement: Allegro OAuth device flow component tests
The system SHALL include a Vitest + React Testing Library test suite for the Allegro OAuth device flow in `InstanceSettings`, covering flow initiation, 202 pending status polling, 200 success completion, popup opening, and API error handling.

#### Scenario: Device flow polling success
- **WHEN** the frontend initiates the Allegro device flow and receives 202 (pending) then 200 (success)
- **THEN** the component SHALL update its state from "polling" to "connected" and open the device verification URL

#### Scenario: Device flow API error
- **WHEN** the device flow API returns a 500 error
- **THEN** the component SHALL display an error message and stop polling without entering an infinite loop

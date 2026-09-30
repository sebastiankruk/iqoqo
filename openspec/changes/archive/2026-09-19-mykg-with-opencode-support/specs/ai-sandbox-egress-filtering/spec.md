## ADDED Requirements

### Requirement: Agent-Aware Egress Allowlist Selection
The sandbox egress proxy SHALL support agent-aware allowlist selection, permitting only the network endpoints required by the currently active AI agent backend (agy/Google or opencode/opencode Go).

#### Scenario: OpenCode daemon allows only opencode Go API endpoints
- **WHEN** the `mykg-opencode-daemon` is the active agent backend
- **THEN** the egress proxy SHALL permit outbound connections ONLY to `api.opencode.ai:443`, `opencode.ai:443`, and any opencode Go authentication/telemetry endpoints explicitly listed in the opencode allowlist
- **AND** all Google/Gemini endpoints SHALL be blocked when opencode is the active agent

#### Scenario: AgY daemon allows only Google/Gemini endpoints (unchanged)
- **WHEN** the `mykg-agy-daemon` is the active agent backend
- **THEN** the egress proxy SHALL permit outbound connections ONLY to the existing Google/Gemini allowlist entries
- **AND** opencode Go API endpoints SHALL be blocked when agy is the active agent

#### Scenario: Allowlist selection driven by environment variable
- **WHEN** the sandbox proxy container starts
- **THEN** it SHALL read the `AI_AGENT` environment variable to determine which allowlist configuration to load
- **AND** the proxy SHALL fail closed (deny all egress) if the `AI_AGENT` value is unrecognized or the corresponding allowlist file is missing

## MODIFIED Requirements

### Requirement: Gemini-Only Network Egress Isolation
The AI sandbox container environment SHALL restrict all outbound network traffic exclusively to verified Google Gemini API, Google OAuth authentication endpoints, and Antigravity verification domains without broad wildcard domains. All other outbound public Internet traffic SHALL be blocked.

#### Scenario: Outbound connection to Google Gemini API succeeds

- **WHEN** the autonomous daemon inside the AI sandbox initiates an HTTPS connection to `generativelanguage.googleapis.com`, `cloudcode-pa.googleapis.com`, `daily-cloudcode-pa.googleapis.com`, `autopush-cloudcode-pa.sandbox.googleapis.com`, `oauth2.googleapis.com`, `accounts.google.com`, `antigravity-unleash.goog`, `antigravity.google`, `www.googleapis.com`, `play.googleapis.com`, `lh3.googleusercontent.com`, or `fonts.gstatic.com`
- **THEN** the connection SHALL be permitted through the egress filter and succeed

#### Scenario: Outbound connection to unauthorized external host is blocked

- **WHEN** any process inside the AI sandbox attempts an outbound TCP or UDP connection to an unauthorized external IP, domain, or port, including unauthenticated storage or form services like `storage.googleapis.com` or `docs.google.com`
- **THEN** the connection SHALL be rejected or dropped by the network egress policy

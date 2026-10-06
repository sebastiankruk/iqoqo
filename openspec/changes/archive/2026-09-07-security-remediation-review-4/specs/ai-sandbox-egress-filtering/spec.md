## MODIFIED Requirements

### Requirement: Gemini-Only Network Egress Isolation
The AI sandbox container environment SHALL restrict all outbound network traffic exclusively to verified Google Gemini API, Google OAuth authentication endpoints, and Antigravity verification domains without broad wildcard domains. All other outbound public Internet traffic SHALL be blocked.

#### Scenario: Outbound connection to Google Gemini API succeeds

- **WHEN** the autonomous daemon inside the AI sandbox initiates an HTTPS connection to `generativelanguage.googleapis.com`, `cloudcode-pa.googleapis.com`, `daily-cloudcode-pa.googleapis.com`, `autopush-cloudcode-pa.sandbox.googleapis.com`, `oauth2.googleapis.com`, `accounts.google.com`, `antigravity-unleash.goog`, `antigravity.google`, `www.googleapis.com`, `play.googleapis.com`, `lh3.googleusercontent.com`, or `fonts.gstatic.com`
- **THEN** the connection SHALL be permitted through the egress filter and succeed

#### Scenario: Outbound connection to unauthorized external host is blocked

- **WHEN** any process inside the AI sandbox attempts an outbound TCP or UDP connection to an unauthorized external IP, domain, or port, including unauthenticated storage or form services like `storage.googleapis.com` or `docs.google.com`
- **THEN** the connection SHALL be rejected or dropped by the network egress policy

### Requirement: Inbound Daemon Prompt Sanitization and Egress Guardrails
The `mykg-agy-daemon` SHALL sanitize incoming task payloads and inject explicit egress guardrail instructions to prevent prompt-injection driven data exfiltration and buffer stall.

#### Scenario: Incoming task containing googleapis.com or exfiltration URLs is sanitized

- **WHEN** a task prompt delivered to the daemon contains URLs pointing to `googleapis.com`, Google Drive, Google Docs, cloud storage endpoints, or unbroken base64 data URIs/binary blobs
- **THEN** the daemon SHALL redact or neutralize the domains and binary blobs prior to executing the `agy` CLI process

#### Scenario: Prompt execution includes security policy guardrail

- **WHEN** the daemon constructs the prompt invocation for `agy`
- **THEN** the prompt SHALL include explicit security guardrail instructions directing the agent never to transmit data or credentials to external network addresses

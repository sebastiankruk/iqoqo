## ADDED Requirements

### Requirement: AI Cover Generator Circuit Breaker

The AI cover generation script (`scripts/generate_ai_covers.py`) SHALL track failures to prevent infinite retry loops that waste LLM tokens and risk rate limits. When a generation fails, the system SHALL increment a `failed_llm_attempts` counter in the manifestation's `meta` JSON. If an item exceeds a defined threshold (e.g. 3 attempts), the script SHALL skip the item on future runs unless explicitly overridden with a `--force-retry` flag.

#### Scenario: Script skips repeatedly failing items

- **WHEN** the batch script processes an item that has `failed_llm_attempts >= 3` in its `meta` payload
- **THEN** the script SHALL skip generation for that item and proceed to the next, conserving LLM tokens

#### Scenario: Script retries on force flag

- **WHEN** the operator invokes the script with `--force-retry`
- **THEN** the script SHALL ignore the `failed_llm_attempts` counter and attempt to generate the cover

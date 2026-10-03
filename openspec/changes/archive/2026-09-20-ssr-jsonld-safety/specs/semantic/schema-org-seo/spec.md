## ADDED Requirements

### Requirement: Safe SSR JSON-LD Serialization

All server-rendered JSON-LD scripts MUST serialize catalog, profile, and shared-collection values for an HTML script context, so untrusted values cannot terminate the script while the resulting payload remains valid JSON-LD.

#### Scenario: Catalog title contains a script terminator

- **WHEN** a Work, Expression, Manifestation, or Item title contains `</script>` or equivalent HTML-sensitive characters
- **THEN** the SSR document contains a valid JSON-LD script whose parsed value preserves the title and cannot execute markup outside the script

#### Scenario: User profile contains HTML-sensitive text

- **WHEN** a public profile display name or bio contains HTML-sensitive characters
- **THEN** the profile page emits parseable JSON-LD without creating an executable script boundary

#### Scenario: Shared collection contains HTML-sensitive text

- **WHEN** a shared collection name, description, or author contains HTML-sensitive characters
- **THEN** the shared page emits parseable JSON-LD without executing or truncating the payload

#### Scenario: All structured-data entry points use the safe boundary

- **WHEN** SSR renders collection, Work, Expression, Manifestation, Item, profile, or shared-collection structured data
- **THEN** every entry point uses the same safe serialization contract and retains its existing Schema.org fields

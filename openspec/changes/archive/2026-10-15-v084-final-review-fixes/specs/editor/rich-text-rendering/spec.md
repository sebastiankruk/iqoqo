## MODIFIED Requirements

### Requirement: Safe Rich Text and Markdown Description Rendering

The system SHALL sanitize and render description fields containing Markdown and HTML content safely, preventing script execution while displaying formatted text across catalog views. During Next.js Server-Side Rendering (SSR) passes when DOMPurify window context is unavailable, the fallback sanitization SHALL strip `<script>` and `<style>` blocks (including their inner contents) and sanitize or entity-encode remaining tags to prevent SSR XSS vulnerabilities and raw payload leakage into the server markup stream.

#### Scenario: Rendering markdown formatted descriptions

- **WHEN** a manifestation or work description contains Markdown markup (such as headings, bold text, lists, or links)
- **THEN** the system SHALL render formatted HTML elements corresponding to the Markdown syntax

#### Scenario: Neutralizing malicious script tags

- **WHEN** a description field contains embedded `<script>`, `onerror=`, or other executable HTML payloads
- **THEN** the system SHALL strip or neutralize the malicious elements prior to rendering

#### Scenario: Neutralizing malicious tags during server-side rendering (SSR)

- **WHEN** a description containing `<script>alert(1)</script>` or malformed tags is processed during an SSR pass where `window` is undefined
- **THEN** the system SHALL completely strip the script tags and their inner body, emitting safe plain text without executing scripts or injecting unescaped tags.

#### Scenario: Preserving plain text readability

- **WHEN** a description contains simple unformatted text
- **THEN** the system SHALL render the text in paragraph form preserving line breaks without markup leakage

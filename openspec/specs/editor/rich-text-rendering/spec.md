## Purpose

Provides secure client-side sanitization and markdown rendering for rich text description fields alongside accurate value binding for FRBR editor selection controls.

## Requirements

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

### Requirement: FRBR Editor Expression Value Binding and Auto-Selection

The FRBR editor SHALL correctly bind and display the currently assigned Expression values when inspecting or editing an entity hierarchy.

#### Scenario: Auto-selecting expression values on form load

- **WHEN** an operator navigates to the Expression editor tab for a manifestation with an existing Expression
- **THEN** the editor dropdowns SHALL automatically reflect the current expression content type, kind, and language values

#### Scenario: Synchronizing expression updates on form submission

- **WHEN** an operator modifies expression properties in the dropdown and submits the form
- **THEN** the system SHALL dispatch the updated attributes to the backend API and update the active editor state

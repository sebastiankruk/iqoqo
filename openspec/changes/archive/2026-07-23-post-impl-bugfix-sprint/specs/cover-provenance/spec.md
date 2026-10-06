---
type: Concept
title: spec
timestamp: 2026-07-23T00:47:00Z
---

## MODIFIED Requirements

### Requirement: Enhanced Fallback Cover Generation

The system SHALL generate visually polished fallback covers when all external API and LLM cover tiers fail. The fallback cover MUST include: a deterministic gradient background derived from the identifier, the title and author rendered with readable typography and drop shadows, and a prominent "powered by iqoqo" graphical footer centered at the bottom of the image. The footer MUST use a font size of at least 28px and be visually prominent. The cover SHALL NOT include a "Placeholder — contribute a cover" call-to-action text, as this adds visual noise without actionable value.

#### Scenario: Fallback cover generated for a new item with no external cover

- **WHEN** the cover pipeline exhausts all external API and LLM tiers for a manifestation
- **THEN** the system SHALL generate a fallback cover with a deterministic gradient, title, author, and a prominent "powered by iqoqo" footer, saving it to the covers directory with `cover_source` set to `"fallback_pil"`.

#### Scenario: Fallback cover footer is visually prominent

- **WHEN** a fallback cover is generated
- **THEN** the "powered by iqoqo" footer text SHALL be rendered at a minimum font size of 28px, centered horizontally, with a subtle horizontal rule or decorative element above it, and use a visible contrast color against the gradient background.

#### Scenario: Fallback cover does NOT include call-to-action text

- **WHEN** a fallback cover is generated
- **THEN** the cover SHALL NOT contain "Placeholder — contribute a cover" or any other call-to-action text.

#### Scenario: Deterministic gradient consistency

- **WHEN** the fallback cover is generated twice for the same identifier and title
- **THEN** the system SHALL produce the identical gradient color palette both times.

#### Scenario: Long title word wrapping

- **WHEN** a manifestation title exceeds the available width for single-line rendering
- **THEN** the system SHALL word-wrap the title across multiple lines within the image margins.

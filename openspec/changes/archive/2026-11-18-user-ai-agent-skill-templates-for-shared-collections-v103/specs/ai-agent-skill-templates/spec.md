## ADDED Requirements

### Requirement: Sanitized HiFi & Physical Music Advisor Skill Template

The repository SHALL provide a copy-pasteable end-user AI skill template at `docs/gems/hifi-music-advisor-skill.md` derived from the workflow in `.context/notes/marketing/skills/hifi-setup-advisor.md` with zero personal hardware, room, or maintenance-gear identifiers (`PMA-1700NE`, `AVR-3313`, `DBT-3313`, `Debut Evo 2`, `nuBox 681`, `DS-301`, `AW-993`, `CS-411`, `XR-65A95L`, `Melodika`, `QE1890`, `QE6111`, `QE6033`, `PGD-4015`, `4001985507832`, `Wash'n'Play`, `Xiaomi Smartmi`, or `Audyssey MultEQ XT32`). The template SHALL provide structured `<YOUR_...>` configuration placeholders, Vinyl vs. CD/SACD mastering and dynamic range advisory rules, duplicate-avoidance checks via iqoqo FRBR metadata, and explicit instructions for both query-free `/share/<token>/jsonld/1..N` browsing and HTTP Content Negotiation (`Accept: application/ld+json`).

#### Scenario: Hardware-agnostic template contains placeholders without personal gear

- **WHEN** `docs/gems/hifi-music-advisor-skill.md` is inspected
- **THEN** it MUST contain `<YOUR_` setup placeholders for amplifier/AVR, turntable, digital transport/DAC, speakers/subwoofer, room calibration, and record-care workflow, MUST preserve the Vinyl vs. CD/SACD mastering/DR decision rules, and MUST NOT contain any hardcoded personal device or cable identifiers listed above.

#### Scenario: Browser-agent and HTTP Content Negotiation collection ingestion instructions

- **WHEN** an AI agent uses `docs/gems/hifi-music-advisor-skill.md` on a `/share/<token>` URL
- **THEN** the template MUST instruct browser-based agents (`Gemini App`, `ChatGPT`, `Claude Web`) NOT to invent query strings, to discover `/share/<token>/jsonld/1..N` links from `<nav aria-label="AI JSON-LD pages">` / `JSON-LD / AI Feed` and `<nav aria-label="JSON-LD Pages">`, to parse `<pre id="jsonld-payload">` (`totalItems`, `perPage`, `totalPages`, `nextPage`, `pages`, and compact keys `t`, `a`, `f`, `l`, `c`, `y`, `g`), and MUST also document `Accept: application/ld+json` and `/api/public/rdf/share/<token>?format=jsonld&limit=2000` for header-capable CLI/MCP clients.

### Requirement: Companion Multi-Domain Skill Templates for iqoqo Shared Collections

The repository SHALL provide end-user skill templates in `docs/gems/` for iqoqo's other primary collection domains—`docs/gems/reading-curator-skill.md` (Books, Comics & Graphic Novels), `docs/gems/boardgame-sommelier-skill.md` (Board Games, Tabletop, LEGO & Puzzles), and `docs/gems/cinema-archivist-skill.md` (Movies, 4K UHD / Blu-ray / DVD & Video Games). Every template SHALL parameterize user preferences via `<YOUR_...>` placeholders, explain FRBR Work -> Expression -> Manifestation -> Item ownership reasoning, document how compact JSON-LD keys (`t`, `a`, `f`, `l`, `c`, `y`, `g`) map to that domain on `/share/<token>/jsonld/<page>` alongside HTTP Content Negotiation (`Accept: application/ld+json`), and forbid fabricating unverified items or editions.

#### Scenario: Domain skill templates include unified semantic reader protocol and anti-hallucination guardrails

- **WHEN** `docs/gems/reading-curator-skill.md`, `docs/gems/boardgame-sommelier-skill.md`, and `docs/gems/cinema-archivist-skill.md` are reviewed
- **THEN** each file MUST include `<YOUR_...>` customization slots, MUST document the query-free `/share/<token>/jsonld/1..N` multi-page traversal protocol and compact `@context` field mappings (`t`, `a`, `f`, `l`, `c`, `y`, `g`), MUST mention `Accept: application/ld+json` for programmatic agents, and MUST instruct the agent never to guess unparsed pages or fabricate catalog entries.

### Requirement: Discovery Cross-Links in Semantic Web Documentation and Librarian Gem

`docs/SEMANTIC_WEB.md`, `docs/tutorials/linked-data-integration.md`, and `docs/gems/iqoqo-librarian-gem.md` SHALL link to the end-user skill templates in `docs/gems/` and document `/share/<token>/jsonld/1..N` paginated discovery so collectors know how to pair shared iqoqo links with both headerless consumer AI apps and header-capable RDF/PAT clients.

#### Scenario: User discovers domain skill templates from Semantic Web guides

- **WHEN** a user reads `docs/SEMANTIC_WEB.md` or `docs/tutorials/linked-data-integration.md`
- **THEN** both documents MUST include a "Ready-to-Use AI Agent & Gem Skill Templates" section linking to `hifi-music-advisor-skill.md`, `reading-curator-skill.md`, `boardgame-sommelier-skill.md`, `cinema-archivist-skill.md`, and `iqoqo-librarian-gem.md`, and `docs/gems/iqoqo-librarian-gem.md` MUST document `/share/<token>/jsonld/1..N` alongside private PAT endpoints.

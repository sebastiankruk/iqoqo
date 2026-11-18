## Why

Collectors who organize physical media in iqoqo (Vinyl/CD/SACD music, Books & Graphic Novels, Board Games & LEGO, Movies/4K UHD & Video Games) want to pair their public shared collections (`/share/<token>`) with personal AI agents—such as Google Gemini Gems, ChatGPT Custom GPTs, Claude Projects, or CLI skills.

However, live testing with consumer LLM web browsers (Gemini App `browsing:browse`) proved that generic web prompts fail on shared collections unless the skill explicitly handles browser tool constraints: no custom `Accept: application/ld+json` headers, HTML-only extraction (`PERMISSION_DENIED` on raw JSON/RDF), `<script>` and `<svg>` DOM stripping, a ~60-item practical ceiling per page, and strict query-string/URL-construction guardrails. As a result, agents must be instructed to follow iqoqo's query-free `/share/<token>/jsonld/1` through `/share/<token>/jsonld/<N>` pages (`perPage: 60`) exposed in `<nav aria-label="AI JSON-LD pages">` and `<nav aria-label="JSON-LD Pages">`.

Furthermore, the author's proven `@hifi-setup-advisor` skill (`.context/notes/marketing/skills/hifi-setup-advisor.md`) contains hardcoded personal hardware (Denon PMA-1700NE/AVR-3313/DBT-3313, Pro-Ject Debut Evo 2, Nubert nuBox 681/DS-301/AW-993, Sony XR-65A95L, QED/Melodika/Profigold/InAkustik cables, Xiaomi Smartmi humidifier, Analogis Wash'n'Play 2) and must be published as a sanitized, hardware-agnostic end-user template alongside companion templates for other iqoqo media domains.

## What Changes

- **Batch 1 — Sanitized End-User Skill & Gem Templates (`docs/gems/`):**
  - `docs/gems/hifi-music-advisor-skill.md`: Hardware-agnostic **HiFi & Physical Music Collection Advisor** skill template derived from `.context/notes/marketing/skills/hifi-setup-advisor.md`. Replaces all personal equipment with copy-pasteable `<YOUR_...>` setup placeholders (`<YOUR_STEREO_AMP>`, `<YOUR_SURROUND_AVR>`, `<YOUR_TURNTABLE_AND_CARTRIDGE>`, `<YOUR_DIGITAL_TRANSPORT_AND_DAC>`, `<YOUR_SPEAKERS_AND_SUB>`, `<YOUR_ROOM_AND_CALIBRATION>`), preserves the audiophile Vinyl vs. CD/SACD mastering/DR decision framework and troubleshooting guidance, and embeds the exact `/share/<token>/jsonld/1..N` + `Accept: application/ld+json` traversal protocol.
  - `docs/gems/reading-curator-skill.md`: **Books, Comics & Graphic Novels Reading Curator** skill template leveraging `schema:Book` / `ComicStory` semantics (ISBN/EAN `gtin13`, publisher, publication year, format/binding, reading backlog prioritization, series order, and edition/translation comparison).
  - `docs/gems/boardgame-sommelier-skill.md`: **Board Games, Tabletop, LEGO & Puzzles Sommelier** skill template leveraging shared manifestation/publisher metadata for player-count matching, playtime/complexity fitting, game-night curation, and expansion compatibility checks.
  - `docs/gems/cinema-archivist-skill.md`: **Physical Cinema (4K UHD / Blu-ray / DVD) & Video Games Archivist** skill template leveraging pressing/release metadata (studio/publisher, release format, catalog number, `gtin13` EAN/UPC) for edition/transfer comparison and home-theater playback advice.
  - `docs/gems/iqoqo-librarian-gem.md`: Update the existing private-PAT Librarian Gem template to reference the public `/share/<token>/jsonld/1..N` multi-page ingestion protocol as a zero-auth option alongside authenticated OpenAPI actions.
- **Batch 2 — Semantic Web & Tutorial Cross-Links (`docs/SEMANTIC_WEB.md`, `docs/tutorials/linked-data-integration.md`):**
  - Add a **Ready-to-Use AI Agent & Gem Skill Templates** section in `docs/SEMANTIC_WEB.md` and `docs/tutorials/linked-data-integration.md` linking all four domain templates (`hifi-music-advisor-skill.md`, `reading-curator-skill.md`, `boardgame-sommelier-skill.md`, `cinema-archivist-skill.md`) plus `iqoqo-librarian-gem.md`, explaining how collectors customize placeholders and paste their `/share/<token>` URL.

## Capabilities

### New Capabilities

- `ai-agent-skill-templates`: Reusable, setup-parameterized end-user AI skill and Gem templates (Music/HiFi, Books/Comics, Board Games/Tabletop, Cinema/Video Games) engineered to ingest iqoqo shared collections via `/share/<token>/jsonld/1..N` and HTTP Content Negotiation (`Accept: application/ld+json`).

### Modified Capabilities

<!-- Cross-links added to existing Semantic Web documentation and docs/gems/iqoqo-librarian-gem.md -->

## Impact

- **End-User Skill Templates:** `docs/gems/hifi-music-advisor-skill.md`, `docs/gems/reading-curator-skill.md`, `docs/gems/boardgame-sommelier-skill.md`, `docs/gems/cinema-archivist-skill.md`, `docs/gems/iqoqo-librarian-gem.md`
- **Documentation:** `docs/SEMANTIC_WEB.md`, `docs/tutorials/linked-data-integration.md`
- **Tests / Lint:** verified with `make secret-scan` and `make lint` (including `markdownlint`)

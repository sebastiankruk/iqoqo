## Context

See `proposal.md`, `.context/notes/marketing/skills/hifi-setup-advisor.md`, and `.context/notes/AI/gemini/Jsonld-load-test.md`. With C118 (`shared-collection-semantic-audio-graph-and-ai-feed-v103`), every public iqoqo share link (`/share/<token>`) exposes:

1. **Human UI with hidden AI discovery index:** `<nav aria-label="AI JSON-LD pages" className="sr-only">` and the W3C RDF icon button linking to query-free `https://<host>/share/<token>/jsonld/1..N`.
2. **Chromeless JSON-LD Mini-Pages (`/share/<token>/jsonld/<page>`):** Serves `text/html` containing `<nav aria-label="JSON-LD Pages">` with windowed query-free absolute URLs (`1`, up to `8` around current page, `totalPages`) and `<pre id="jsonld-payload">` with 60 minified items per page using short `@context` keys (`t` = title/name, `a` = creator/byArtist, `f` = format/content_type, `l` = publisher/recordLabel, `c` = catalogNumber, `y` = datePublished, `g` = gtin13) plus `totalItems`, `page`, `perPage`, `totalPages`, `nextPage`, and `pages`.
3. **Standard Content Negotiation (`Accept: application/ld+json` / `application/json+ld`) & `/share/<token>/catalog.jsonld`:** Available to CLI scripts, MCP servers, and Custom Actions that can set HTTP headers or fetch non-HTML MIME types.

End users often struggle to write reliable system prompts/skills because:
- Consumer LLM web fetchers refuse URLs invented by the model or containing `?` query strings in discovered pagination links.
- Different collectors have completely different hardware, bookshelves, or gaming preferences, whereas reference skills (such as `.context/notes/marketing/skills/hifi-setup-advisor.md`) naturally contain one person's specific room and gear.

## Goals / Non-Goals

**Goals:**

- Publish four clean, portable, vendor-neutral Markdown skill templates in `docs/gems/` tailored to Gemini Gems, Claude Skills/Projects, Custom GPTs, and OpenCode/CLI skills.
- Strip 100% of the author's personal equipment, room measurements, brand-specific cables, and private collection assumptions from `hifi-music-advisor-skill.md`, replacing them with clear `<YOUR_...>` placeholders and examples of how to fill them in.
- Standardize a shared, battle-tested **iqoqo Semantic Collection Reader** protocol across all four templates covering both headerless browser agents (`/share/<token>/jsonld/1..N`) and header-capable HTTP/RDF clients (`Accept: application/ld+json`, `/share/<token>/catalog.jsonld`, `/api/public/rdf/share/<token>`).
- Ground every template in iqoqo's FRBR hierarchy (`Work -> Expression -> Manifestation -> Item`) so agents accurately distinguish works from physical pressings/editions and avoid buying duplicates.

**Non-Goals:**

- Changing backend API endpoints or frontend share routes (handled in C118).
- Storing personal API keys, PATs, share tokens, or private user collections inside repository files.
- Building an interactive web UI wizard inside Next.js (can be layered later on top of these canonical Markdown templates).

## Decisions

1. **Consistent Four-Part Skill Architecture (`docs/gems/*-skill.md`):**
   Every template in `docs/gems/` uses the same four portable sections so users can copy the Markdown verbatim into any LLM platform:
   - **Role & When to Use:** Clear domain scope and activation triggers.
   - **Personal Setup & Preferences (`<YOUR_...>` Placeholders):** Explicit fill-in-the-blank configuration block (hardware chain & room for Music/HiFi; reading languages, preferred bindings, shelf goals for Books; player count, time budget, complexity ceiling for Board Games; screen/audio setup & region coding for Cinema/Games) with short instructions reminding the user to replace or delete unused slots.
   - **Reading iqoqo Shared Collections (`/share/<token>`):** Dual-mode ingestion block:
     - *Mode A — Browser AI Agents (Gemini App / ChatGPT Web / Claude Web):* Open `/share/<token>`, locate the query-free `/share/<token>/jsonld/1` link and `<nav aria-label="AI JSON-LD pages">`, fetch all `/share/<token>/jsonld/1..N` pages (`perPage = 60`), read `<pre id="jsonld-payload">`, and map the compact `@context` keys (`t`, `a`, `f`, `l`, `c`, `y`, `g`) without inventing URLs or appending `?query` params.
     - *Mode B — HTTP / CLI / MCP / API Clients:* Send `GET /share/<token>` with `Accept: application/ld+json` (or fetch `/share/<token>/catalog.jsonld` or `/api/public/rdf/share/<token>?format=jsonld&limit=2000`), optionally paired with PAT `/api/items` actions from `iqoqo-librarian-gem.md`.
   - **Domain Advisory Rules & Anti-Hallucination Guardrails:** Strict instruction to cite exact pressing/edition fields (`f`, `l`, `c`, `y`, `g`) observed in JSON-LD, report `totalItems` honestly if pagination was incomplete, and never hallucinate ownership or unverified catalog/mastering claims.

2. **Sanitization Boundary for `hifi-music-advisor-skill.md`:**
   - Replace every concrete consumer device and cable from `.context/notes/marketing/skills/hifi-setup-advisor.md` with generic `<YOUR_...>` tokens and role descriptions (e.g., `<YOUR_INTEGRATED_AMP_OR_PREAMP>`, `<YOUR_AVR_OR_PROCESSOR>`, `<YOUR_TURNTABLE_AND_CARTRIDGE>`, `<YOUR_DIGITAL_SOURCE_AND_DAC>`, `<YOUR_SPEAKERS_AND_SUBWOOFER>`, `<YOUR_CLEANING_AND_CARE_TOOLS>`, `<YOUR_ROOM_ACOUSTICS_AND_DSP>`).
   - Keep the high-value domain reasoning intact: signal-path discipline (pure analog/stereo vs. multichannel bypass), dynamic range & mastering lineage comparison for Vinyl vs. CD/SACD recommendations, duplicate-prevention against existing owned pressings, and maintenance/humidification awareness gated on what the user fills in.

3. **Companion Domain Templates:**
   - **`reading-curator-skill.md` (Books, Comics & Graphic Novels):** Focuses on FRBR Work/Expression/Manifestation separation (same story across translations, omnibuses, hardcovers, paperbacks), series reading order, ISBN/EAN (`g`) edition verification, and backlog/mood curation.
   - **`boardgame-sommelier-skill.md` (Board Games, Tabletop, LEGO & Puzzles):** Uses shared game/set entries (`t`, `a` designer/brand, `f` game/set subtype, `l` publisher/line, `c` set/product number, `y`, `g`) alongside user group profile (`<YOUR_TYPICAL_PLAYER_COUNT>`, `<YOUR_SESSION_TIME_MINUTES>`, `<YOUR_COMPLEXITY_TOLERANCE>`) for table-fit picks, expansion matching, and duplicate prevention.
   - **`cinema-archivist-skill.md` (Movies, 4K UHD / Blu-ray & Video Games):** Uses shared disc/cartridge release entries (`t`, `a` director/developer, `f` 4k_uhd/blu_ray/dvd/video_game, `l` studio/distributor, `c` release/catalog SKU, `y`, `g`) paired with user playback profile (`<YOUR_DISPLAY_AND_HDR_SUPPORT>`, `<YOUR_AUDIO_DECODER_AND_SPEAKERS>`, `<YOUR_CONSOLES_AND_REGIONS>`) for transfer/edition upgrades and watchlist curation.

4. **Discovery from Canonical Docs:**
   - Update `docs/gems/iqoqo-librarian-gem.md` so users combining private PAT actions with public share links know about `/share/<token>/jsonld/1..N`.
   - Add a **Ready-to-Use AI Agent & Gem Skill Templates** section to `docs/SEMANTIC_WEB.md` and `docs/tutorials/linked-data-integration.md`.

## Risks / Trade-offs

- **[Risk] Schema mismatch between non-audio items and compact JSON-LD `@context` aliases** -> Mitigation: Explicitly document in every template that `share-server.tsx` uses unified short keys (`a` for creator/author/designer/director mapped from `authors`, `f` for format/content_type, `l` for publisher/studio/recordLabel, `c` for catalog_number, `g` for EAN/UPC/ISBN) so agents parse Books, Games, and Movies identically without confusion.
- **[Risk] Personal setup accidentally leaks into published repo docs** -> Mitigation: Add an explicit spec requirement and pre-commit check forbidding hardware identifiers from `.context/notes/marketing/skills/hifi-setup-advisor.md` inside `docs/gems/hifi-music-advisor-skill.md`, keeping `.context/` strictly local and gitignored.
- **[Risk] Very large collections (> 10 pages / 600+ items)** -> Mitigation: Document the 10-page sliding window (`<nav aria-label="JSON-LD Pages">` and `pages`/`nextPage`): instruct browser agents to follow `nextPage` or paginated window links page-by-page until `page === totalPages`, or recommend HTTP `Accept: application/ld+json` / `/share/<token>/catalog.jsonld` for programmatic clients.

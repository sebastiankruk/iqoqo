## 1. Batch 1 — Sanitized End-User Skill & Gem Templates (`docs/gems/`)

- [x] 1.1 Author `docs/gems/hifi-music-advisor-skill.md` from `.context/notes/marketing/skills/hifi-setup-advisor.md`, replacing all personal equipment, cable, room, and maintenance gear details with `<YOUR_...>` placeholders and embedding the `/share/<token>/jsonld/1..N` + `Accept: application/ld+json` collection-reading protocol plus Vinyl vs. CD/SACD mastering rules.
- [x] 1.2 Author `docs/gems/reading-curator-skill.md` for Books, Comics, and Graphic Novels (`schema:Book` / `ComicStory`), mapping compact JSON-LD keys (`t`, `a`, `f`, `l`, `c`, `y`, `g`) to reading lists, edition/translation checks, and series order.
- [x] 1.3 Author `docs/gems/boardgame-sommelier-skill.md` for Board Games, Tabletop, LEGO sets, and Puzzles (`schema:Game` / `Product`), parameterizing player count, session duration, and complexity weight alongside shared `/share/<token>/jsonld/1..N` ingestion.
- [x] 1.4 Author `docs/gems/cinema-archivist-skill.md` for Physical Cinema (`4K UHD`, `Blu-ray`, `DVD`) and Video Games (`schema:Movie` / `VideoGame`), covering home-theater/console placeholders, release transfer comparisons, and catalog/barcode verification via `/share/<token>/jsonld/1..N`.
- [x] 1.5 Update `docs/gems/iqoqo-librarian-gem.md` to reference the zero-auth `/share/<token>/jsonld/1..N` multi-page traversal option and link to the four domain skill templates.

## 2. Batch 2 — Semantic Web & Tutorial Cross-Links

- [x] 2.1 Add a "Ready-to-Use AI Agent & Gem Skill Templates" section to `docs/SEMANTIC_WEB.md` explaining browser (`Gemini App`, `ChatGPT`, `Claude`) vs. header-capable (`Accept: application/ld+json`, PAT) agent setup and linking all templates in `docs/gems/`.
- [x] 2.2 Add the template quickstart and `/share/<token>/jsonld/1..N` multi-page note to `docs/tutorials/linked-data-integration.md` (Step 4: AI Agent Integration & Next Steps).

## 3. Batch 3 — Verification

- [x] 3.1 Verify zero personal gear leaks from `.context/notes/marketing/skills/hifi-setup-advisor.md` into `docs/gems/`, and verify all new/updated documentation passes `IQOQO_AI_MODE=1 make secret-scan` and `IQOQO_AI_MODE=1 make lint` (including `markdownlint`).

## Context

Version 0.8.0 introduces major Semantic Web features but documentation has not kept pace. Users cannot safely upgrade without migration documentation, and new features are unusable without guides. The CHANGELOG is incomplete, and the README roadmap is outdated. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Create migration guide enabling safe upgrades from v0.7.x to v0.8.0
- Complete CHANGELOG with all v0.8.0 features following Keep a Changelog standards
- Create comprehensive Semantic Web guide for users and developers
- Update README with current feature status and Semantic Web section
- Document new environment variables (BASE_URL) in INSTALL.md
- Create API reference for new endpoints
- Update ARCHITECTURE.md with Semantic Web layer
- Create OPERATIONS.md for ETL and audit scripts
- Add tutorial content for new features

**Non-Goals:**
- Create video tutorials (separate effort)
- Translate documentation to other languages (future i18n effort)
- Document internal implementation details (focus on user-facing)
- Create exhaustive API reference for all existing endpoints (only new ones)

## Decisions

### Decision 1: Separate migration guide document
**Choice:** Create `docs/UPGRADE_0.8.0.md` rather than adding to existing UPGRADE.md
**Rationale:** Major version-specific changes (F3 column promotion) deserve dedicated guide; easier to find and reference
**Alternatives considered:** Single UPGRADE.md with sections (harder to navigate), inline in CHANGELOG (not detailed enough)

### Decision 2: Semantic Web guide as single document
**Choice:** Create `docs/SEMANTIC_WEB.md` covering all Semantic Web features
**Rationale:** Features are related and users need holistic understanding; easier to maintain than separate docs
**Alternatives considered:** Separate docs for each feature (fragmented, harder to find), wiki pages (less discoverable)

### Decision 3: API reference format
**Choice:** Create `docs/API.md` with endpoint documentation in markdown tables
**Rationale:** Markdown tables are readable, searchable, and can be rendered nicely; follows common API doc patterns
**Alternatives considered:** OpenAPI/Swagger spec (more setup, overkill for current needs), separate page per endpoint (fragmented)

### Decision 4: Tutorial directory structure
**Choice:** Create `docs/tutorials/` directory with separate tutorial files
**Rationale:** Tutorials are distinct from reference docs; directory structure allows easy addition of more tutorials
**Alternatives considered:** Single tutorial document (hard to navigate), inline in feature docs (not step-by-step enough)

### Decision 5: CHANGELOG format
**Choice:** Follow Keep a Changelog (https://keepachangelog.com/) format
**Rationale:** Industry standard, machine-readable, familiar to developers
**Alternatives considered:** Custom format (non-standard), GitHub releases only (not in repo)

### Decision 6: Documentation priority
**Choice:** Prioritize migration guide and CHANGELOG as release blockers
**Rationale:** Users cannot safely upgrade without migration guide; CHANGELOG is expected for releases
**Alternatives considered:** All docs equally important (delays release), tutorials first (less critical)

## Risks / Trade-offs

**[Risk] Documentation becomes outdated quickly** → Mitigation: Include documentation updates in PR checklist, assign doc reviewers
**[Risk] Migration guide misses edge cases** → Mitigation: Test migration on staging with production-like data, include troubleshooting section
**[Risk] API reference incomplete** → Mitigation: Focus on new endpoints first, existing endpoints documented in future release
**[Risk] Tutorials too basic or too advanced** → Mitigation: Target intermediate users, include prerequisites and expected outcomes
**[Trade-off] Comprehensive docs vs release delay** → Accept 1-day delay for critical docs (migration guide, CHANGELOG, Semantic Web guide); defer nice-to-have docs
**[Trade-off] Separate docs vs single document** → Accept separate docs for better organization; users prefer focused documents over monolithic ones

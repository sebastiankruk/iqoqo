## MODIFIED Requirements

### Requirement: Native Manifest Hardening, Tooling Safety & Documentation/Skills Integrity

Android and iOS project manifests SHALL disable cloud auto-backup (`android:allowBackup="false"`), align `minSdkVersion = 26`, `versionName = "1.0.0"`, `MARKETING_VERSION = 1.0.0`, and `ExampleInstrumentedTest.java` package assertion (`"cc.iqoqo.app"`) with `docs/MOBILE_TARGETS.md`, omit deprecated 32-bit `armv7` from `Info.plist`, use `mktemp -d` + SHA-256 verification in `scripts/setup-android-sdk.sh`, declare `repair-authors` in `Makefile` `.PHONY`, URL-encode Allegro `affiliate_url` query strings via `urllib.parse.quote_plus()`, and keep all AI Skills, Gemini Gems, `CHANGELOG.md`, `MOBILE_SIDELOAD.md`, and `v1.0.0` roadmap checkboxes (`C95`–`C100g`) synchronized and free of duplicate `v0.9.3` sections.

#### Scenario: AI Skills and Gems integrity test enforces zero duplicate Upcoming sections

- **GIVEN** all `.agents/skills/*/SKILL.md` and `.gemini/gems/*.md` files
- **WHEN** `pytest tests/test_ai_skills_integrity.py` runs
- **THEN** every persona skill and gem contains exactly one `## Upcoming` section targeting `v1.0.0`–`v1.0.2` and zero stale `## Upcoming (v0.9.3 & Beyond)` headings.

#### Scenario: Allegro candidate normalization URL-encodes multi-word affiliate queries

- **GIVEN** an Allegro product or offer without a barcode is normalized using free-text query `"Wiedźmin & Miecz Przeznaczenia"`
- **WHEN** `_normalize_allegro_product` or `_normalize_allegro_offer` constructs `affiliate_url`
- **THEN** the `string` query parameter is URL-encoded with `urllib.parse.quote_plus()` (`https://allegro.pl/listing?string=Wied%C5%BAmin+%26+Miecz+Przeznaczenia`).

#### Scenario: Makefile declares repair-authors in .PHONY and Android test asserts cc.iqoqo.app

- **GIVEN** `Makefile` and `ExampleInstrumentedTest.java`
- **WHEN** `pytest tests/test_mobile_readiness.py` runs
- **THEN** `Makefile` includes `repair-authors` in `.PHONY` and `ExampleInstrumentedTest.java` asserts `"cc.iqoqo.app"`.

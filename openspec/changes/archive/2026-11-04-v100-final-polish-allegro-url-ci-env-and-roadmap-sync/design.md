## Context

Following the merge of `C100d` (#402), `C100e` (#403), and `C100f` (#404) into `release/1.0.0`, the final `/code-reviewer` audit confirmed 0 Critical and 0 Moderate findings and surfaced 4 minor Low/cosmetic items (`proposal.md` - Why). Addressing them in `C100g` closes 100% of all findings recorded in `.context/notes/review/1.0.0/release-1.0.0-review-pr-392.md`.

## Goals / Non-Goals

**Goals:**

- Ensure `affiliate_url` in `app/utils/allegro.py` safely URL-encodes `barcode or query` via `urllib.parse.quote_plus`.
- Eliminate direct `${{ github.ref_name }}` shell interpolation inside `run:` steps of `.github/workflows/mobile-build.yml`, add `concurrency` group cancellation, and include `repair-authors` in `Makefile` `.PHONY`.
- Align `ExampleInstrumentedTest.java` package assertion with `"cc.iqoqo.app"`.
- Synchronize `docs/CHANGELOG.md` (5-tab bottom navigation note) and check off all `v1.0.0` (`C95`–`C100g`) checkboxes in `.context/notes/iqoqo roadmap.md`, `.context/notes/iqoqo development notes.md`, and `.context/notes/plan/1.0.x-release-plan.md`.

**Non-Goals:**

- Altering Allegro OAuth or Catalog API search endpoints (only the returned `affiliate_url` string is URL-encoded).
- Modifying iOS or Android native runtime routing logic (already verified in `C100f`).

## Decisions

1. **Use `urllib.parse.quote_plus(str(barcode or query))` in `app/utils/allegro.py`:**
   - *Rationale*: When `extracted["barcode"]` is present it is an alphanumeric EAN/ISBN, for which `quote_plus` is a no-op; when `barcode` is missing and `query` is a multi-word title (e.g., `"Dune & Messiah"`), `quote_plus` encodes spaces as `+` and `&` as `%26`, preventing query-parameter truncation on `https://allegro.pl/listing?string=...`.
2. **Bind `REF_NAME: ${{ github.ref_name }}` via `env:` in `.github/workflows/mobile-build.yml`:**
   - *Rationale*: Passing untrusted or user-controlled GitHub Actions context expressions (`github.ref_name`) through environment variables rather than inline shell strings prevents shell injection and satisfies GitHub Actions security hardening rules. Adding `concurrency: { group: mobile-build-${{ github.ref }}, cancel-in-progress: true }` prevents redundant `macos-15` runner queue contention on rapid branch pushes.

## Risks / Trade-offs

- **[Risk] Existing unit tests expecting unencoded spaces in Allegro `affiliate_url`** → *Mitigation*: Inspect and update `tests/test_allegro.py` while adding explicit coverage for multi-word/special-character queries.

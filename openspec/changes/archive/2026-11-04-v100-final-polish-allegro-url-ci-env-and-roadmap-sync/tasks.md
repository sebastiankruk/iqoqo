## 1. Allegro Affiliate URL Encoding

- [x] 1.1 Update `_normalize_allegro_product()` and `_normalize_allegro_offer()` in `app/utils/allegro.py` to URL-encode `barcode or query` using `urllib.parse.quote_plus(str(barcode or query))` when constructing `affiliate_url`, and verify with unit tests in `tests/test_allegro.py`.

## 2. Mobile CI Workflow, Makefile & Android Scaffold Test Hardening

- [x] 2.1 Update `.github/workflows/mobile-build.yml` to add top-level `concurrency` (`group: mobile-build-${{ github.ref }}`, `cancel-in-progress: true`) and bind `REF_NAME: ${{ github.ref_name }}` via `env:` instead of inline `${{ github.ref_name }}` in `run:` blocks, and add `repair-authors` to `.PHONY` in `Makefile`.
- [x] 2.2 Update `frontend/android/app/src/androidTest/java/com/getcapacitor/myapp/ExampleInstrumentedTest.java` to assert `"cc.iqoqo.app"`, and verify both workflow and Android test assertions in `tests/test_mobile_readiness.py`.

## 3. Release 1.0.0 Documentation & Roadmap Completion

- [x] 3.1 Update `docs/CHANGELOG.md` line 15 to describe the 5 persistent mobile bottom navigation tabs (`Home`, `Scan`, `Collection`, `Search`, `Profile` / `Sign In`), and check off `[ ]` -> `[x]` for all completed `v1.0.0` (`C95`–`C100`) items in `.context/notes/iqoqo roadmap.md`, `.context/notes/iqoqo development notes.md`, and `.context/notes/plan/1.0.x-release-plan.md`.
- [x] 3.2 Run `IQOQO_AI_MODE=1 make lint`, `IQOQO_AI_MODE=1 make secret-scan`, and `IQOQO_AI_MODE=1 .venv/bin/pytest tests/test_allegro.py tests/test_mobile_readiness.py` to verify all checks pass.

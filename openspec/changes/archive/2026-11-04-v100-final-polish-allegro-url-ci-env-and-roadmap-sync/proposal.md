## Why

During the final pre-release `/code-reviewer` verification pass for `v1.0.0`, four low-severity polish items were identified across Allegro URL formatting, GitHub Actions shell variable interpolation, Android scaffold test metadata, and `v1.0.0` roadmap/changelog documentation alignment. Resolving them in a dedicated OpenSpec change (`C100g`) ensures `v1.0.0` ships with zero outstanding findings of any severity.

## What Changes

- **Allegro `affiliate_url` Query Parameter Encoding (`app/utils/allegro.py`)**: Encode `barcode or query` via `urllib.parse.quote_plus(str(barcode or query))` in `_normalize_allegro_product()` and `_normalize_allegro_offer()` so free-text title searches containing spaces or reserved characters (`&`, `+`, `?`) produce RFC 3986-compliant URLs.
- **GitHub Actions `mobile-build.yml` `env:` Hardening & `Makefile` `.PHONY` Alignment (`.github/workflows/mobile-build.yml`, `Makefile`)**: Pass `REF_NAME: ${{ github.ref_name }}` via `env:` instead of interpolating `${{ github.ref_name }}` directly inside `run:` shell commands, add workflow `concurrency` cancellation (`mobile-build-${{ github.ref }}`), and add `repair-authors` to `.PHONY` in `Makefile`.
- **Android Instrumented Test Package Alignment (`ExampleInstrumentedTest.java`)**: Update `frontend/android/app/src/androidTest/java/com/getcapacitor/myapp/ExampleInstrumentedTest.java` to assert `"cc.iqoqo.app"` instead of the default Capacitor template `"com.getcapacitor.app"`.
- **Release `v1.0.0` Changelog & Planning Checkboxes Alignment (`docs/CHANGELOG.md`, `.context/notes/iqoqo roadmap.md`, `.context/notes/iqoqo development notes.md`, `.context/notes/plan/1.0.x-release-plan.md`)**: Update `docs/CHANGELOG.md` line 15 to reflect the 5 persistent mobile bottom navigation tabs (`Home`, `Scan`, `Collection`, `Search`, `Profile` / `Sign In`), mark all `v1.0.0` (`C95`–`C100`) tasks as `[x]` completed in `.context/notes/iqoqo roadmap.md` and `.context/notes/iqoqo development notes.md`, and register `C100g` in `.context/notes/plan/1.0.x-release-plan.md`.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `mobile-shell-routes-scanner-and-ci`: Extend `Native Manifest Hardening, Tooling Safety & Documentation/Skills Integrity` to require URL-encoded Allegro `affiliate_url` query strings, `env:` variable binding in `.github/workflows/mobile-build.yml`, `"cc.iqoqo.app"` package assertion in `ExampleInstrumentedTest.java`, and completed `v1.0.0` roadmap checkboxes.

## Impact

- **Backend**: `app/utils/allegro.py`, `tests/test_allegro.py`
- **Mobile & CI**: `.github/workflows/mobile-build.yml`, `Makefile`, `frontend/android/app/src/androidTest/java/com/getcapacitor/myapp/ExampleInstrumentedTest.java`, `tests/test_mobile_readiness.py`
- **Documentation & Planning**: `docs/CHANGELOG.md`, `.context/notes/iqoqo roadmap.md`, `.context/notes/iqoqo development notes.md`, `.context/notes/plan/1.0.x-release-plan.md`

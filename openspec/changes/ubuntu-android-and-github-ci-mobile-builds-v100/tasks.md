## 1. Ubuntu Android SDK/Emulator Scripts & Makefile Targets

- [ ] 1.1 Create `scripts/setup-android-sdk.sh` to install/verify Android `cmdline-tools`, `platform-tools`, `platforms;android-35`, and `build-tools;35.0.0` on Ubuntu Linux.
- [ ] 1.2 Create `scripts/setup-android-emulator.sh` (supporting Linux `$HOME/.android-sdk` and macOS `$HOME/Library/Android/sdk` defaults) to provision and boot the `iqoqo-test` headless AVD.
- [ ] 1.3 Add `mobile-build`, `mobile-sync`, `mobile-android-apk`, `mobile-android-aab`, `mobile-adb-install`, and `test-e2e-mobile` targets to `Makefile` respecting `IQOQO_AI_MODE=1`.

## 2. GitHub Actions Workflow & Documentation

- [ ] 2.1 Create `.github/workflows/mobile-build.yml` with `build-android` (`ubuntu-latest` $\to$ `.apk`) and `build-ios` (`macos-15` $\to$ unsigned `.xcarchive` + `iqoqo-ios-sideload.ipa`) jobs triggered on `v1.*` tags, `release/1.*` branches, and `workflow_dispatch`.
- [ ] 2.2 Author `docs/MOBILE_SIDELOAD.md` and `docs/MOBILE_TARGETS.md`.

## 3. Verification & Tests

- [ ] 3.1 Author BATS tests in `tests/bash/mobile_scripts.bats` and extend `tests/bash/scripts_syntax.bats` to validate `scripts/setup-android-sdk.sh` and `scripts/setup-android-emulator.sh`.
- [ ] 3.2 Extend `tests/test_infra_config.py` to verify `.github/workflows/mobile-build.yml` and Makefile mobile targets.
- [ ] 3.3 Run `IQOQO_AI_MODE=1 make lint` and `IQOQO_AI_MODE=1 make test`.

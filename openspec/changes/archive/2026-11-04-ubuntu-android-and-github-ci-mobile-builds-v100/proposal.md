## Why
To ship installable Android (`.apk` / `.aab`) and iOS (`.ipa` / `.xcarchive`) mobile apps in `v1.0.0`, we need a repeatable headless Android build/emulator/ADB pipeline on our local Ubuntu machine AND a multi-OS GitHub Actions workflow (`ubuntu-latest` for Android + `macos-15` for iOS Xcode) that produces sideloadable binaries without requiring paid store accounts upfront.

## What Changes

- **Headless Ubuntu Android SDK & Emulator Provisioning (`scripts/setup-android-sdk.sh`, `scripts/setup-android-emulator.sh`):** Provide idempotent setup scripts for Ubuntu Linux that bootstrap OpenJDK 21 and Android `cmdline-tools` (`platform-tools`, `platforms;android-35`, `build-tools;35.0.0`) in `$HOME/.android-sdk` and optionally launch a headless Android emulator (`iqoqo-test`) or connect via ADB Wi-Fi to a physical Pixel device.
- **Makefile Mobile Targets:** Add `IQOQO_AI_MODE=1`-aware targets to `Makefile`: `mobile-build`, `mobile-sync`, `mobile-android-apk`, `mobile-android-aab`, `mobile-adb-install`, and `test-e2e-mobile`.
- **GitHub Actions Multi-Platform Mobile CI (`.github/workflows/mobile-build.yml`):** Build and upload `iqoqo-android-debug.apk` on `ubuntu-latest` (Node 22 + Temurin Java 21 + Gradle) and `iqoqo-ios-sideload.ipa` + `.xcarchive` on `macos-15` (Node 22 + Xcode `CODE_SIGNING_ALLOWED=NO` + Payload `.ipa` packaging) on `v1.*` tags, `release/1.*` branches, and `workflow_dispatch`.
- **Documentation (`docs/MOBILE_SIDELOAD.md`, `docs/MOBILE_TARGETS.md`):** Document headless Ubuntu APK compilation, ADB Wi-Fi Pixel installation, macOS/AltStore/Sideloadly iOS installation, and the iOS 15+ / Android API 26+ hardware compatibility baseline.

## Capabilities

### New Capabilities
- `ubuntu-android-and-ci-mobile-builds`: Headless Ubuntu Android SDK/Gradle/ADB toolchain, GitHub Actions Android (`.apk`) + iOS (`.ipa`/`.xcarchive`) CI pipeline, and sideloading/target documentation.

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

- `Makefile`
- `.github/workflows/mobile-build.yml`
- `scripts/setup-android-sdk.sh`, `scripts/setup-android-emulator.sh`
- `docs/MOBILE_SIDELOAD.md`, `docs/MOBILE_TARGETS.md`
- `tests/bash/mobile_scripts.bats`, `tests/test_infra_config.py`

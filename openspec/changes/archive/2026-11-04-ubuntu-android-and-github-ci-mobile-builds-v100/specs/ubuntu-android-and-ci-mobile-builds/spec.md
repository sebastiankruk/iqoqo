## Purpose
Provide reproducible local Ubuntu Android SDK/Gradle/ADB build tooling and GitHub Actions CI workflows producing installable Android (`.apk`) and iOS (`.ipa` / `.xcarchive`) artifacts.

## ADDED Requirements

### Requirement: Headless Ubuntu Android Build & ADB Targets

The repository SHALL provide `scripts/setup-android-sdk.sh`, `scripts/setup-android-emulator.sh`, and Makefile targets (`mobile-build`, `mobile-sync`, `mobile-android-apk`, `mobile-adb-install`) enabling headless compilation and installation of the Android APK on Ubuntu Linux.

#### Scenario: Developer builds Android APK on Ubuntu
- **GIVEN** Android SDK command-line tools and Java 21 are configured via `scripts/setup-android-sdk.sh`
- **WHEN** `make mobile-android-apk` is executed
- **THEN** Next.js exports static assets (`CAPACITOR_BUILD=true`), Capacitor syncs `frontend/android/`, and Gradle outputs `app-debug.apk`.

### Requirement: Multi-Platform GitHub Actions Mobile Build Pipeline

`.github/workflows/mobile-build.yml` SHALL build and upload an Android `.apk` artifact on `ubuntu-latest` and an unsigned iOS `.ipa` + `.xcarchive` artifact on `macos-15`.

#### Scenario: Mobile CI workflow runs on `v1.0.0` tag or manual dispatch
- **GIVEN** `.github/workflows/mobile-build.yml` is triggered
- **WHEN** `build-android` and `build-ios` jobs complete
- **THEN** `iqoqo-android-debug-*` (`.apk`) and `iqoqo-ios-sideload-*` (`.ipa` and `.xcarchive.zip`) artifacts are uploaded with 30-day retention.

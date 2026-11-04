## Context

Our primary development workstation is an Ubuntu Linux box (which cannot run Apple Xcode natively), while GitHub Actions provides both `ubuntu-latest` and `macos-15` runners. We need a zero-friction workflow to build and test Android `.apk` binaries locally on Ubuntu (and install them over ADB to a Pixel phone or headless emulator) while compiling both Android `.apk` and iOS `.ipa`/`.xcarchive` packages in GitHub CI.

## Goals / Non-Goals

**Goals:**
- Enable `make mobile-android-apk` and `make mobile-adb-install` directly on this Ubuntu box via `scripts/setup-android-sdk.sh`.
- Produce downloadable `iqoqo-android-debug.apk` and `iqoqo-ios-sideload.ipa` / `.xcarchive` artifacts in `.github/workflows/mobile-build.yml`.
- Validate shell scripts with BATS (`tests/bash/mobile_scripts.bats`) and workflow configuration with pytest (`tests/test_infra_config.py`).

**Non-Goals:**
- Paid Apple Developer ($99/yr) or Google Play ($25) store submission credentials in `v1.0.0` (deferred to `v1.0.2` `C110`).

## Decisions

### Unsigned `.xcarchive` + Payload `.ipa` Repackaging on `macos-15` CI
* **Decision:** In `.github/workflows/mobile-build.yml`, run `xcodebuild -project ios/App/App.xcodeproj -scheme App -configuration Release -destination "generic/platform=iOS" -archivePath build/iqoqo.xcarchive archive CODE_SIGNING_ALLOWED=NO`, then copy `build/iqoqo.xcarchive/Products/Applications/App.app` into `Payload/App.app` and zip it as `iqoqo-ios-sideload.ipa`.
* **Rationale:** Tools like AltStore, SideStore, and Sideloadly consume an unsigned `.ipa` directly and sign it with the user's free Apple ID on their device/computer, whereas local Xcode users can open `.xcarchive`. Producing both artifacts in CI makes iOS testing on iPhone/iPad effortless.

## Risks / Trade-offs

- **Risk:** Android Gradle requires specific Java and SDK versions on Ubuntu.
  - **Mitigation:** `scripts/setup-android-sdk.sh` pins Temurin/OpenJDK 21 and Android SDK `platforms;android-35` + `build-tools;35.0.0` in `$HOME/.android-sdk` without requiring root if JDK 21 is present (or prompts clearly).

# Mobile Sideloading Guide — iqoqo v1.0.0

This document describes how to build, install, and sideload the iqoqo native mobile app
(Android and iOS) without requiring paid store accounts upfront.

---

## Prerequisites

| Tool                         | Version            | Required for                                |
|------------------------------|--------------------|---------------------------------------------|
| Node.js                      | 22+                | Next.js build, static export, Capacitor     |
| npm                          | 10+                | Dependency management                       |
| Java (JDK)                   | 21 (Temurin)       | Android Gradle 8 build                      |
| Android SDK                  | API 35 (15)        | Android build-tools 35.0.0, `adb`, emulator |
| Xcode                        | 16+                | iOS build (macOS only)                      |
| AltStore or Sideloadly       | Latest             | iOS sideloading with free Apple ID          |
| `adb` (Android Debug Bridge) | Latest             | USB / Wi-Fi device deployment               |

---

## One-Time Workstation Provisioning

### Ubuntu Linux (Local Workstation)

Bootstrap Android SDK `cmdline-tools`, `platform-tools`, `platforms;android-35`, and `build-tools;35.0.0` into `$HOME/.android-sdk`:

```bash
./scripts/setup-android-sdk.sh
```

To configure your shell environment:

```bash
export ANDROID_HOME="$HOME/.android-sdk"
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH"
```

To spin up a headless Android emulator for integration testing:

```bash
./scripts/setup-android-emulator.sh
```

---

## Build & Sync

Rebuild the conditional static export and sync native assets to Android and iOS projects:

```bash
# Using Makefile:
make mobile-sync

# Or manually:
cd frontend
CAPACITOR_BUILD=true npm run build
npx cap sync
```

---

## Android — Debug APK & Direct Installation

### Compile APK

```bash
# Using Makefile:
make mobile-android-apk

# Or directly in Gradle:
cd frontend/android
./gradlew assembleDebug
```

Output: `frontend/android/app/build/outputs/apk/debug/app-debug.apk`

### Install to Physical Device via ADB

1. Enable **Developer Options** on device: `Settings -> About Phone -> Tap Build Number 7 times`.
2. Enable **USB Debugging** (or **Wireless Debugging**).
3. Connect device:

   ```bash
   adb devices
   ```

4. Install app:

   ```bash
   make mobile-adb-install
   ```

### Compile Release AAB (Play Store Ready)

```bash
make mobile-android-aab
```

Output: `frontend/android/app/build/outputs/bundle/release/app-release.aab`

---

## iOS — Direct Sideloading (macOS or AltStore / Sideloadly)

### Method A — Direct Run in Xcode (Free Apple ID)

1. Open iOS workspace in Xcode:

   ```bash
   cd frontend
   npx cap open ios
   ```

2. In Xcode:
   - Go to **App** target -> **Signing & Capabilities**.
   - Under **Team**, select your personal Apple ID (free accounts work for device testing).
   - Select your connected iPhone or iPad.
   - Click **Run** (`⌘R`).
3. On your iPhone: go to `Settings -> General -> VPN & Device Management` and tap **Trust [Your Apple ID]**.

### Method B — Unsigned IPA via AltStore / SideStore / Sideloadly

1. Download `iqoqo-ios-sideload-*.ipa` from GitHub Actions artifacts (produced by `.github/workflows/mobile-build.yml`).
2. Sideload using:
   - **AltStore** ([altstore.io](https://altstore.io)): Send `.ipa` to device or drag into AltServer.
   - **Sideloadly** ([sideloadly.io](https://sideloadly.io)): Connect iOS device, select `.ipa`, enter Apple ID credentials, click **Start**.

> Note: Free Apple ID developer certificates expire after 7 days. AltStore will automatically refresh certificates when running on your local Wi-Fi.

---

## GitHub Actions Automated Mobile CI

The workflow `.github/workflows/mobile-build.yml` runs automatically on `v1.*` tags, `release/1.*` branches, and manual `workflow_dispatch`:

| Artifact | Runner | Format | Retention |
| :--- | :--- | :--- | :--- |
| `iqoqo-android-debug-*` | `ubuntu-latest` | `.apk` (debug binary) | 30 days |
| `iqoqo-ios-sideload-*` | `macos-15` | `.ipa` (unsigned) & `.xcarchive.zip` | 30 days |

---

## Server Selection & Mobile Authentication

On first launch, the iqoqo native mobile app presents the **Server Selector** screen.
Enter your server address (e.g. `https://iqoqo.example.com`). The client queries `GET /api/health` and `GET /api/auth/providers` to confirm availability.

- **Sign in with Apple:** Supported on iOS native and macOS; returns credentials to `/auth-exchange`.
- **Google OAuth:** Redirects through system browser and deep-links back via `iqoqo://auth-exchange#token=...`.
- **Local Credentials / 2FA:** Authenticates directly and stores JWT securely in `@capacitor-community/secure-storage`.

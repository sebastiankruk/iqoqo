# Mobile Sideloading Guide — iqoqo v0.8.0

This document describes how to build and sideload the iqoqo native mobile app
(iOS and Android) without an Apple Developer Account or Google Play Console.

---

## Prerequisites

| Tool                         | Version            | Required for                      |
| ---------------------------- | ------------------ | --------------------------------- |
| Node.js                      | 20+                | npm install, Next.js build        |
| npm                          | 10+                | package management                |
| Java (JDK)                   | 17+                | Android Gradle build              |
| Android Studio               | Latest             | Android SDK, `adb`, emulator      |
| Xcode                        | 16+                | iOS build (macOS only)            |
| CocoaPods                    | Latest             | iOS dependency resolution         |
| AltStore or Sideloadly       | Latest             | iOS sideload without $99 account  |
| `adb` (Android Debug Bridge) | SDK Platform Tools | Android device install            |

Install CocoaPods if missing:

```bash
sudo gem install cocoapods
```

---

## One-Time Setup

### 1. Install npm packages

```bash
cd frontend
npm install
```

### 2. Scaffold native platform projects (first time only)

```bash
cd frontend
npx cap add android    # creates frontend/android/
npx cap add ios        # creates frontend/ios/ (macOS only)
```

> These directories are git-ignored. Re-run after a fresh clone or when
> adding/removing Capacitor plugins.

---

## Build & Sync

Every time frontend code changes, rebuild the static export and sync to native:

```bash
# Using the Makefile shortcut (from repo root):
make mobile-sync

# Or manually:
cd frontend
CAPACITOR_BUILD=true npm run build   # Next.js static export → frontend/out/
npx cap sync                          # copies out/ into android/ and ios/
```

---

## Android — Debug APK (Sideload)

### Build

```bash
cd frontend/android
./gradlew assembleDebug
```

Output: `frontend/android/app/build/outputs/apk/debug/app-debug.apk`

### Install via ADB

```bash
# Enable USB Debugging on device: Settings → Developer options → USB Debugging
adb devices          # confirm device is listed
adb install frontend/android/app/build/outputs/apk/debug/app-debug.apk
```

### Install via file transfer

1. Copy `app-debug.apk` to the device (USB, Bluetooth, cloud drive, etc.)
2. On the device: Settings → **Install from unknown sources** → enable for your
   file manager app
3. Tap the APK to install

---

## iOS — Direct USB Install (Xcode, free Apple ID)

This method requires macOS + Xcode but **no $99 Apple Developer Account**.

### Method A — Run directly from Xcode (easiest)

```bash
cd frontend
npx cap open ios    # opens ios/App/App.xcworkspace in Xcode
```

In Xcode:

1. **Signing & Capabilities** tab → **Team**: select your personal Apple ID
   (free accounts work for direct device install)
2. Connect your iPhone via USB and select it as the run target
3. **Product → Run** (`⌘R`) — Xcode builds and installs in one step
4. On the iPhone: **Settings → General → VPN & Device Management** → trust the
   developer certificate

### Method B — Export IPA then use AltStore

```bash
cd frontend
npx cap open ios
```

In Xcode:

1. **Product → Archive** — produces an `.xcarchive`
2. **Distribute App → Development → Export** — produces an `.ipa` file

Then in AltStore ([altstore.io](https://altstore.io)) on your Mac:

- Drag the `.ipa` into the AltStore window, or
- Use **AltServer** (runs in menu bar) to install directly to the device

### Method C — Sideloadly (Windows or macOS)

1. Download [Sideloadly](https://sideloadly.io) for your OS
2. Build the IPA following Method B above
3. Open Sideloadly, drag the IPA, select your device, sign in with Apple ID
4. Click **Start**

> Apps installed via free Apple ID expire after 7 days. Re-install to refresh.
> AltStore handles re-signing automatically if AltServer is running on your network.

---

## Makefile Quick Reference

All commands run from the **repo root**:

```bash
make mobile-build        # Next.js static export only
make mobile-sync         # build + cap sync (both platforms)
make mobile-ios          # sync + open Xcode
make mobile-android      # sync + open Android Studio
make mobile-run-ios      # sync + deploy to connected iOS device
make mobile-run-android  # sync + deploy to connected Android device
```

---

## CI/CD Sideload Artifacts

The GitHub Actions workflow `.github/workflows/mobile-build.yml` triggers on
`v0.8.*` tags or `workflow_dispatch` and produces:

| Artifact                     | Platform | Retention |
| ---------------------------- | -------- | --------- |
| `app-debug.apk`              | Android  | 30 days   |
| `iqoqo.xcarchive` (unsigned) | iOS      | 30 days   |

The xcarchive is unsigned (`CODE_SIGNING_ALLOWED=NO`). To install it, open the
archive in Xcode (`File → Open`) and re-export with your own signing identity,
or sign it locally with `codesign`.

---

## Backend Instance URL

The native app uses a **HASS-style server selector** on first launch. Enter the
full URL of your iqoqo backend instance (e.g. `https://iqoqo.example.com`).

The app calls `GET /api/health` to verify the instance before saving. Ensure
the backend is reachable from the device's network.

---

## Troubleshooting

| Problem                                        | Fix                                                                  |
| ---------------------------------------------- | -------------------------------------------------------------------- |
| `cap sync` fails — plugins not found           | Run `npm install` in `frontend/` first                               |
| Xcode: "No signing certificate"                | Signing & Capabilities → add personal Apple ID team                  |
| Android: "INSTALL_FAILED_UPDATE_INCOMPATIBLE"  | `adb uninstall cc.iqoqo.app` then re-install                         |
| App white-screens on launch                    | Check that `frontend/out/index.html` exists after build              |
| Deep links not working (Android)               | Verify `intent-filter` in `AndroidManifest.xml` after `cap sync`     |
| Auth loop after OAuth                          | Verify `NEXT_PUBLIC_FRONTEND_URL` points to the backend instance     |

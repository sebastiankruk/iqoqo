# Mobile Sideloading Guide — iqoqo v1.0.0

This document describes how to build, install, and sideload the iqoqo native mobile app
(Android and iOS) without requiring paid store accounts upfront.

---

## Prerequisites

| Tool                         | Version      | Required for                                         |
|------------------------------|--------------|------------------------------------------------------|
| Node.js                      | 22+          | Next.js build, static export, Capacitor              |
| npm                          | 10+          | Dependency management                                |
| Java (JDK)                   | 21 (Temurin) | Android Gradle 8 build                               |
| Android SDK                  | API 35 (15)  | Android build-tools 35.0.0, `adb`, emulator          |
| Xcode                        | 16+          | iOS build & device deployment (macOS only)           |
| CocoaPods                    | 1.11+        | iOS native dependency sync (`make mobile-ios-setup`) |
| `adb` (Android Debug Bridge) | Latest       | USB / Wi-Fi Android device deployment                |

---

## One-Time Workstation Provisioning

### macOS (iOS Workstation)

Bootstrap CocoaPods tooling without compiling LLVM or Ruby from source:

```bash
make mobile-ios-setup
```

*(Runs `scripts/setup-ios-tools.sh` using pinned user gems compatible with macOS system Ruby).*

Ensure your user gem directory is in your shell `PATH` by adding it to `~/.zshrc`:

```bash
export PATH="$(ruby -e 'puts Gem.bindir(Gem.user_dir)'):$PATH"
```

### Ubuntu Linux (Android Workstation)

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

## iOS — Direct Device Deployment (Xcode)

This is the standard, secure deployment path using only official Apple development tools. No third-party sideloading utilities or paid developer accounts are required.

### 1. Connect & Pair Device

1. Connect your iPhone or iPad to your Mac via USB cable.
2. On your device, unlock the screen and tap **Trust This Computer** when prompted, then enter your device passcode.
3. In Xcode, open **Window -> Devices and Simulators** (`⇧⌘2`), select your device, and ensure pairing completes.
   *(Alternatively run `xcrun devicectl manage pair --device "<Device Name>"` in terminal).*

### 2. Enable Developer Mode (iOS / iPadOS 16+)

Apple hides the Developer Mode toggle in Settings until the device is paired with a host Mac:

1. On your iPhone or iPad, go to **Settings -> Privacy & Security**.
2. Scroll to the bottom and tap **Developer Mode**.
3. Toggle the switch **ON** and tap **Restart**.
4. After the device reboots and you unlock it, tap **Turn On** on the confirmation prompt and enter your passcode.

### 3. Build & Open Xcode Workspace

Sync the static web bundle and open the CocoaPods workspace in Xcode:

```bash
make mobile-ios-open
```

> **IMPORTANT:** Always open `frontend/ios/App/App.xcworkspace`, never `App.xcodeproj`. Opening `.xcodeproj` directly will fail with missing CocoaPods configurations.

### 4. Configure Signing in Xcode

1. In the Xcode left navigator, select the blue **App** project root.
2. Select the **App** target under **TARGETS**, then open the **Signing & Capabilities** tab.
3. Under **Team**, select your personal Apple ID (`Personal Team`).
4. If using a free personal Apple ID and the default `cc.iqoqo.app` bundle identifier conflicts with an existing app, append a personal suffix to the **Bundle Identifier** (e.g., `cc.iqoqo.app.<yourname>`).

> Note: The repository already configures `IPHONEOS_DEPLOYMENT_TARGET = 15.0` and `ENABLE_USER_SCRIPT_SANDBOXING = NO` in `App.xcodeproj` so CocoaPods framework embedding builds without sandbox permission errors.

### 5. Deploy & Run

1. In the Xcode top toolbar destination menu, choose your connected physical device (e.g. `Sebastian’s iPad`).
2. Click **Run** (`⌘R`).
3. Xcode compiles, codesigns with your free personal certificate, and installs iqoqo directly onto your device.

### 6. First Launch Device Trust

On physical devices deploying with a free Apple ID, iOS blocks launch until the developer certificate is trusted:

1. On your iPhone or iPad, go to **Settings -> General -> VPN & Device Management**.
2. Under **Developer App**, tap your Apple ID email.
3. Tap **Trust "[Your Apple ID]"** and confirm.
4. Launch the **iqoqo** app from your home screen.

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

# Mobile Platform Targets & Compatibility Matrix — iqoqo v1.0.0

This document defines the supported operating systems, hardware baselines, and native device capabilities for the iqoqo native mobile ecosystem across Android and iOS.

---

## Supported Operating Systems

| Platform | Minimum Version | Target Version | Recommended Device Baseline |
| :--- | :--- | :--- | :--- |
| **Android** | Android 8.0 (Oreo, API 26) | Android 15 (Vanilla Ice Cream, API 35) | 3GB+ RAM, 64-bit ARM CPU (`arm64-v8a`) |
| **iOS / iPadOS** | iOS 15.0 | iOS 18.x | iPhone 6s / SE (1st gen) or later; A9 chip+ |

---

## Native Architecture & SDK Configuration

### Android (`frontend/android/`)

- **Compile SDK:** 35 (Android 15)
- **Target SDK:** 35 (Android 15)
- **Minimum SDK:** 26 (Android 8.0)
- **Java Version:** OpenJDK 21 (Temurin)
- **Gradle Version:** 8.x + Android Gradle Plugin 8.7+
- **Architectures:** `arm64-v8a`, `armeabi-v7a`, `x86_64` (emulator)
- **Package ID:** `cc.iqoqo.app`
- **Default Scheme:** `https://localhost`

### iOS (`frontend/ios/`)

- **Minimum Deployment Target:** iOS 15.0
- **Xcode Version:** 16.0+
- **Swift Version:** 5.9+
- **Bundle Identifier:** `cc.iqoqo.app`
- **Default Scheme:** `capacitor://localhost`
- **Deep Link Custom Scheme:** `iqoqo://`

---

## Native Device Capabilities & Permission Mapping

| Feature | Android Permission | iOS Info.plist Key | Fallback / Web Behavior |
| :--- | :--- | :--- | :--- |
| **Camera Viewfinder** | `android.permission.CAMERA` | `NSCameraUsageDescription` | WebRTC `navigator.mediaDevices.getUserMedia` |
| **Cover Photo Upload** | Camera & Media permissions | `NSPhotoLibraryAddUsageDescription` | HTML `<input type="file" accept="image/*">` |
| **Haptic Feedback** | Device vibrator | Taptic Engine | Guarded by `isNativeApp()`, no-op on web |
| **Hardware Torch** | Camera flashlight | AVCaptureDevice torch | Torch toggle disabled when not supported |
| **Secure Token Storage** | Android Keystore / `EncryptedSharedPreferences` | iOS Keychain Services | Guarded; web falls back to session cookies |
| **Deep-Link Authentication** | Intent filter (`iqoqo://auth-exchange`) | CFBundleURLSchemes (`iqoqo`) | Handled client-side on `/auth-exchange` |
| **System Browser OAuth** | Chrome Custom Tabs via `@capacitor/browser` | `ASWebAuthenticationSession` | Standard window redirect |

---

## Hardware Limitations & Known Constraints

1. **Camera Auto-Focus:** Continuous barcode autofocus requires a camera with hardware macro or autofocus capability. On older fixed-focus lenses, barcode detection may require positioning the item 15–20 cm away.
2. **Torch Availability:** Front-facing cameras and devices lacking a physical flash module will automatically hide the torch toggle control in `TopBar`.
3. **Background Processing:** Sideloaded debug builds do not run background metadata ingestion syncs; ingestion jobs run in foreground or on the backend host server.

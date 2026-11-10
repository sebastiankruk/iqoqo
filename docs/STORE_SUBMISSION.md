# Mobile App Store Submission Guide

This document details the configuration, privacy disclosures, and signing procedures for publishing iQoQo native mobile applications to the Apple App Store (and TestFlight) and Google Play Console.

## 1. Privacy Philosophy: Zero Corporate Tracking

iQoQo is an open-source, local-first library cataloging system that honors user data sovereignty.

- **Zero Telemetry / Zero Analytics**: iQoQo contains no advertising SDKs, no behavioral trackers, and no third-party telemetry services.
- **Zero Third-Party Data Sharing**: Data entered into iQoQo is communicated solely to the user's self-hosted instance or federated peer instances chosen by the user.

---

## 2. Apple App Store / iOS Privacy Nutrition

Apple requires an iOS privacy manifest (`PrivacyInfo.xcprivacy`) embedded in the app bundle (`frontend/ios/App/App/PrivacyInfo.xcprivacy`).

### Declared Privacy Manifest Values

- **`NSPrivacyTracking`**: `false` (iQoQo does not track users across other apps or websites).
- **`NSPrivacyTrackingDomains`**: Empty array `[]`.
- **`NSPrivacyCollectedDataTypes`**: Empty array `[]`.
- **`NSPrivacyAccessedAPITypes`**:
  - `NSPrivacyAccessedAPITypeUserDefaults`: Declared with reason code `CA92.1` ("Access user defaults to read and write information that is only accessible to the app itself"). Used by `@capacitor/preferences` to retain local server instance URLs and user interface theme preferences.

### App Store Connect Privacy Questionnaire Answers

When completing the **App Privacy** questionnaire in App Store Connect:

1. **Data Collection**: Select **"No, we do not collect data from this app"** (or indicate that data stored on user-controlled self-hosted servers is not collected by the app developer).
2. **Tracking**: Select **"No, this app does not track users"**.

---

## 3. Google Play Data Safety Declaration

When filling out the **Data safety** section in the Google Play Console:

| Section | Question | Answer | Details |
| :--- | :--- | :--- | :--- |
| **Data collection and security** | Does your app collect or share any of the required user data types? | **No** | Application operates directly against user's self-hosted server without corporate intermediary servers. |
| **Security practices** | Is all user data collected by your app encrypted in transit? | **Yes** | App enforces HTTPS/TLS encryption for all communications. |
| **Security practices** | Do you provide a way for users to request that their data is deleted? | **Yes** | Account deletion is self-serve via profile settings. |

---

## 4. Release Signing & Sideloading

iQoQo supports two distribution modes:

### A. Sideload Artifacts (Zero-Account Builds)

GitHub Actions builds unsigned Android APKs and unsigned iOS xcarchives automatically without requiring any developer credentials. Developers can sideload these artifacts directly:

- **Android**: Install the generated unsigned/debug APK via ADB: `adb install app-debug.apk`.
- **iOS**: Sign the `.xcarchive` locally in Xcode using a free personal Apple ID development team.

### B. Automated Store Signing (Optional Secrets)

To enable automated release signing and store deployment via CI:

1. **Android Play Store**:
   - `ANDROID_KEYSTORE_BASE64`: Base64-encoded release `.keystore` / `.jks`.
   - `ANDROID_KEYSTORE_PASSWORD`: Keystore password.
   - `ANDROID_KEY_ALIAS`: Key alias.
   - `ANDROID_KEY_PASSWORD`: Key password.
2. **Apple App Store / TestFlight**:
   - `APPLE_CERTIFICATE_P12`: Base64-encoded Apple Distribution certificate.
   - `APPLE_CERTIFICATE_PASSWORD`: Certificate password.
   - `APPLE_PROVISIONING_PROFILE`: Base64-encoded mobileprovision profile.
   - `APPLE_APP_SPECIFIC_PASSWORD`: App-specific password or App Store Connect API Key.

When these secrets are omitted in repository settings, the CI workflow gracefully skips signing steps and produces unsigned sideload packages.

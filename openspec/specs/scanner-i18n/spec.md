# scanner-i18n Specification

## Purpose

Define the internationalization requirements for the scanner UI components using next-intl and locale files (`en.json`, `pl.json`).

## Requirements

### Requirement: Scanner camera-capture strings use next-intl

All user-visible strings in `frontend/components/scanner/camera-capture.tsx` SHALL use `next-intl` translation keys via the `useTranslations('scanner')` hook instead of hardcoded English strings.

#### Scenario: Camera capture renders with English locale

- **WHEN** the scanner camera capture component renders with locale set to `en`
- **THEN** all user-visible text SHALL be loaded from `frontend/messages/en.json` under the `scanner.cameraCapture` namespace
- **AND** no hardcoded English strings SHALL remain in the component JSX

#### Scenario: Camera capture renders with Polish locale

- **WHEN** the scanner camera capture component renders with locale set to `pl`
- **THEN** all user-visible text SHALL be loaded from `frontend/messages/pl.json` under the `scanner.cameraCapture` namespace
- **AND** Polish translations SHALL use sentence case (first word capitalized, rest lowercase unless proper nouns)

### Requirement: Scanner bottom-sheet strings use next-intl

All user-visible strings in `frontend/components/scanner/bottom-sheet.tsx` SHALL use `next-intl` translation keys via the `useTranslations('scanner')` hook.

#### Scenario: Bottom sheet renders with English locale

- **WHEN** the scanner bottom sheet component renders with locale set to `en`
- **THEN** all user-visible text SHALL be loaded from `frontend/messages/en.json` under the `scanner.bottomSheet` namespace

#### Scenario: Bottom sheet renders with Polish locale

- **WHEN** the scanner bottom sheet component renders with locale set to `pl`
- **THEN** all user-visible text SHALL be loaded from `frontend/messages/pl.json` under the `scanner.bottomSheet` namespace
- **AND** Polish translations SHALL use sentence case

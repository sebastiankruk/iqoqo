## Purpose

Provides internationalization (i18n) test coverage for new features to ensure all user-facing text is properly translated and locale-aware.

## Requirements

### Requirement: SPARQL Explorer i18n completeness test
The system SHALL have an i18n test that validates all user-facing text in SPARQL Explorer is properly translated.

#### Scenario: All UI elements have translations

- **WHEN** SPARQL Explorer UI is rendered in different locales
- **THEN** all user-facing text has translations and no untranslated strings appear

#### Scenario: Error messages are translated

- **WHEN** error occurs in SPARQL Explorer
- **THEN** error message is displayed in user's locale

### Requirement: Data export UI i18n completeness test
The system SHALL have an i18n test that validates all user-facing text in data export UI is properly translated.

#### Scenario: Export UI has translations

- **WHEN** data export UI is rendered in different locales
- **THEN** all buttons, labels, and messages have translations

#### Scenario: Format names are translated

- **WHEN** export format selection is displayed
- **THEN** format names (JSON-LD, Turtle, JSON) are translated or properly localized

### Requirement: Missing translation detection test
The system SHALL have a test that detects missing translations in new features.

#### Scenario: Missing translation in new component

- **WHEN** new component is added with user-facing text
- **THEN** test detects and reports any missing translations

#### Scenario: Translation key validation

- **WHEN** translation keys are used in components
- **THEN** all keys exist in translation files

### Requirement: Locale switching test
The system SHALL have a test that validates locale switching works correctly for new features.

#### Scenario: Switch locale in SPARQL Explorer

- **WHEN** user switches locale while using SPARQL Explorer
- **THEN** all UI text updates to new locale without page reload

#### Scenario: Switch locale in export UI

- **WHEN** user switches locale while using export UI
- **THEN** all UI text updates to new locale without page reload

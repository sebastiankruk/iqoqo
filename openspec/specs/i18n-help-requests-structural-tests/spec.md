## ADDED Requirements

### Requirement: HelpRequests i18n keys are identical between en.json and pl.json

The `HelpRequests` namespace in `frontend/messages/en.json` and `frontend/messages/pl.json` SHALL contain the exact same set of keys. No key SHALL exist in one language file but not the other.

#### Scenario: All keys match between English and Polish

- **WHEN** the `HelpRequests` namespace is extracted from both `en.json` and `pl.json`
- **THEN** the set of top-level keys SHALL be identical

#### Scenario: No nested key divergence exists

- **WHEN** the `HelpRequests` namespace is compared recursively between `en.json` and `pl.json`
- **THEN** every nested key path in English SHALL have a corresponding key path in Polish

### Requirement: HelpRequests i18n values are non-empty

No `HelpRequests` translation value in either `en.json` or `pl.json` SHALL be an empty string.

#### Scenario: English translations have no empty strings

- **WHEN** all `HelpRequests` values in `en.json` are checked
- **THEN** no value SHALL be an empty string

#### Scenario: Polish translations have no empty strings

- **WHEN** all `HelpRequests` values in `pl.json` are checked
- **THEN** no value SHALL be an empty string

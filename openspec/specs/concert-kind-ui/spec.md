# concert-kind-ui Specification

## Purpose
Specify admin API and FRBR editor UI support for expression kind property selection.
## Requirements
### Requirement: Admin API forwards expression kind

The `PUT /api/admin/frbr/expression/{id}` endpoint SHALL accept an optional `kind` field in the JSON request body and SHALL forward it to `frbr_service.update_expression()`. When `kind` is present, the service SHALL validate it against the `EXPRESSION_KINDS` controlled vocabulary and persist it on the Expression record. When `kind` is absent from the request body, the Expression's existing `kind` SHALL NOT be modified.

#### Scenario: Admin sets expression kind to live_performance

- **WHEN** an authenticated admin sends `PUT /api/admin/frbr/expression/{id}` with body `{"kind": "live_performance"}`
- **THEN** the system SHALL update the Expression's `kind` to `"live_performance"` and return `{"success": true}`

#### Scenario: Admin clears expression kind

- **WHEN** an authenticated admin sends `PUT /api/admin/frbr/expression/{id}` with body `{"kind": ""}`
- **THEN** the system SHALL set the Expression's `kind` to `None` (studio/default) and return `{"success": true}`

#### Scenario: Admin sends invalid kind

- **WHEN** an authenticated admin sends `PUT /api/admin/frbr/expression/{id}` with body `{"kind": "not_a_valid_kind"}`
- **THEN** the system SHALL return a 404/400 error with a message indicating the valid values

#### Scenario: Kind absent from request body

- **WHEN** an authenticated admin sends `PUT /api/admin/frbr/expression/{id}` with body `{"language": "pl"}` (no `kind` key)
- **THEN** the system SHALL update only the language and SHALL NOT modify the Expression's existing `kind`

### Requirement: Escalation system accepts change_type requests

The `_validate_escalation_input()` function in `app/api/social.py` SHALL accept `"change_type"` as a valid `request_type` alongside `"correction"` and `"deletion"`. A `change_type` escalation request SHALL be validated, stored, and resolved through the same approval queue as other escalation types.

#### Scenario: Non-admin submits change_type escalation

- **WHEN** an authenticated non-admin user submits an escalation request with `request_type: "change_type"`
- **THEN** the system SHALL validate and store the request without returning a validation error

#### Scenario: Custodian resolves change_type escalation

- **WHEN** a Custodian accepts a `change_type` escalation request
- **THEN** the system SHALL apply the requested type change to the target entity and mark the request as resolved

### Requirement: FRBR editor exposes expression kind dropdown

The `FrbrEditor` component SHALL render a `<select>` dropdown for `expression.kind` on the Expression tab, populated with all values from the `EXPRESSION_KINDS` controlled vocabulary plus an empty option for studio/default. The dropdown SHALL display the current `kind` value and SHALL dispatch the updated value on form submission alongside other expression fields.

#### Scenario: Admin selects live_performance from kind dropdown

- **WHEN** an admin opens the FRBR editor for an Expression and selects `"live_performance"` from the kind dropdown
- **THEN** the form SHALL include `kind: "live_performance"` in the submission payload to the admin update endpoint

#### Scenario: Admin clears kind via dropdown

- **WHEN** an admin opens the FRBR editor for an Expression with `kind = "live_performance"` and selects the empty/studio option
- **THEN** the form SHALL include `kind: ""` in the submission payload, and the backend SHALL clear the kind

#### Scenario: Kind dropdown reflects current value

- **WHEN** an admin opens the FRBR editor for an Expression that already has `kind = "live_performance"`
- **THEN** the kind dropdown SHALL be pre-selected to `"live_performance"`

### Requirement: One-off data correction script removed

The file `scripts/fix_manifestation_1984.py` SHALL NOT exist in the release branch when merged to `main`. The manifestation-1984 correction it performed is superseded by the general FRBR entity type-change mechanism.

#### Scenario: Release branch does not contain fix script

- **WHEN** the `release/0.7.13` branch is merged to `main`
- **THEN** `scripts/fix_manifestation_1984.py` SHALL NOT be present in the merged tree

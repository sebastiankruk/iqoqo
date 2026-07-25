# deletion-request-submission Specification

## Purpose
Defines the user-facing submission flow for deletion requests within the escalation system: request type selection in the escalation trigger dialog, form adaptation between correction and deletion modes, API input validation for the `request_type` field, and i18n coverage for all deletion-related user labels.
## Requirements
### Requirement: Deletion Request Type Selection in Submission Dialog

The escalation trigger dialog SHALL present a request type selector as the first field, allowing the user to choose between "Metadata Correction" and "Request Deletion" before filling other fields. The default selection SHALL be "Metadata Correction". The radio group SHALL be labeled with an i18n key for accessibility.

#### Scenario: User opens the escalation dialog

- **WHEN** an authenticated user with `escalate:request` permission opens the escalation trigger dialog
- **THEN** the dialog SHALL render a request type radio group with "Metadata Correction" (default) and "Request Deletion" options at the top of the form.

#### Scenario: User selects "Request Deletion"

- **WHEN** the user selects "Request Deletion" in the request type selector
- **THEN** the dialog SHALL hide the field_name, current_value, and suggested_value form fields, and SHALL display a single "Reason for deletion" text area field with a required marker (`*`). The "Reason for deletion" label and placeholder SHALL be rendered using i18n keys.

#### Scenario: User selects "Metadata Correction"

- **WHEN** the user selects "Metadata Correction" in the request type selector
- **THEN** the dialog SHALL display the existing form fields (field_name dropdown, current_value input, suggested_value input with required marker, note text area) exactly as they are rendered currently, with no changes to validation or behavior.

### Requirement: Deletion Request API Submission Contract

The create escalation endpoint SHALL accept an optional `request_type` field in the JSON payload. When `request_type` is `"deletion"`, the endpoint SHALL apply special validation rules. When `request_type` is omitted or `"correction"`, the endpoint SHALL behave identically to the current implementation.

#### Scenario: User submits a deletion request with a reason

- **WHEN** an authenticated user submits a POST to `/api/escalations/<level>/<target_id>` with `request_type: "deletion"`, `note: "This ISBN is for a completely different book — scanned the wrong barcode"`, `field_name: ""`, and `suggested_value: ""`
- **THEN** the system SHALL create an `EscalationRequest` with `request_type="deletion"`, `status="pending"`, the provided `note`, empty `field_name`, empty `suggested_value`, and return HTTP 201 with the created request data including `request_type`.

#### Scenario: User submits a deletion request without a reason note

- **WHEN** an authenticated user submits a POST to `/api/escalations/<level>/<target_id>` with `request_type: "deletion"` but `note` is empty or missing
- **THEN** the system SHALL return HTTP 400 with an error message indicating that a reason is required for deletion requests.

#### Scenario: User submits a deletion request with a reason exceeding max length

- **WHEN** an authenticated user submits a POST to `/api/escalations/<level>/<target_id>` with `request_type: "deletion"` and a `note` exceeding `MAX_SOCIAL_TEXT_LENGTH` (2048 characters)
- **THEN** the system SHALL return HTTP 400 with an error indicating the maximum length constraint.

#### Scenario: User submits a correction request with request_type field

- **WHEN** an authenticated user submits a POST with `request_type: "correction"`, `field_name: "title"`, `suggested_value: "Correct Title"`, and the request passes existing validation
- **THEN** the system SHALL create the escalation with `request_type="correction"` and return HTTP 201.

#### Scenario: User submits without request_type field (backward compatibility)

- **WHEN** an authenticated user submits a POST without a `request_type` field, providing `field_name: "title"` and `suggested_value: "Correct Title"`
- **THEN** the system SHALL default `request_type` to `"correction"`, validate per existing correction rules, and return HTTP 201.

#### Scenario: User submits with invalid request_type value

- **WHEN** an authenticated user submits a POST with `request_type: "invalid_type"` and other required fields
- **THEN** the system SHALL return HTTP 400 with an error message indicating `request_type` must be either `"correction"` or `"deletion"`.

### Requirement: EscalationTrigger Form State Management for Request Type

The `EscalationTrigger` component SHALL manage internal state for the selected request type and SHALL adjust the form payload accordingly before submission. The component SHALL clear form-related state when switching between request types to prevent stale correction-type data from leaking into a deletion request, and vice versa.

#### Scenario: Switching from correction to deletion clears field values

- **WHEN** the user has partially filled correction fields (field_name, suggested_value) and then switches the selector to "Request Deletion"
- **THEN** the dialog SHALL hide the correction fields and SHALL display the "Reason for deletion" field in a clean state. If the user switches back to "Metadata Correction", the correction fields SHALL reappear in their default/initial state (not preserving previously entered values).

#### Scenario: Frontend submits deletion request to API

- **WHEN** the user fills the "Reason for deletion" field and clicks submit with "Request Deletion" selected
- **THEN** the component SHALL call `createEscalation()` with `request_type: "deletion"`, `field_name: ""`, `suggested_value: ""`, `current_value: undefined`, and `note` set to the deletion reason text.

### Requirement: Deletion Request UI Labels and i18n

All user-facing labels for the deletion request feature SHALL be internationalized via the `HelpRequests` i18n namespace in both `en.json` and `pl.json`. The `EscalationTrigger` component SHALL use `useTranslations("HelpRequests")` to access all labels.

#### Scenario: English locale labels render correctly

- **WHEN** the application is set to English (`en`) locale
- **THEN** the request type selector SHALL display "Metadata Correction" and "Request Deletion". The deletion reason field SHALL show label "Reason for deletion" with placeholder text explaining what to describe. The success toast after submission SHALL display "Deletion request submitted to custodians".

#### Scenario: Polish locale labels render correctly

- **WHEN** the application is set to Polish (`pl`) locale
- **THEN** the request type selector SHALL display Polish translations for "Metadata Correction" and "Request Deletion". All labels, placeholders, and toast messages SHALL be in Polish.

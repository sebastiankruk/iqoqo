# feedback-schema-validation Specification

## Purpose

Validate incoming feedback ticket patch requests against a structured schema to reject unauthorized or malformed field updates.

## Requirements

### Requirement: Pydantic/Marshmallow validation for feedback PATCH endpoint
The `PATCH /api/feedback/<id>` endpoint SHALL validate request payloads using Marshmallow schema validation instead of raw `request.get_json()` parsing.

#### Scenario: Valid feedback update payload

- **WHEN** a PATCH request is sent with valid fields (`status`, `feedback_type`, `description`)
- **THEN** the endpoint SHALL accept the payload and update the feedback item
- **AND** the response SHALL return the updated feedback item as JSON

#### Scenario: Invalid feedback update payload with unknown fields

- **WHEN** a PATCH request includes unknown fields not in the schema
- **THEN** the endpoint SHALL return a 400 error with field-level validation messages
- **AND** no database mutation SHALL occur

#### Scenario: Empty PATCH payload

- **WHEN** a PATCH request is sent with an empty JSON body
- **THEN** the endpoint SHALL return a 400 error indicating no valid fields provided

# scanner-policy-intent-separation Specification

## Purpose

Enforce strict architectural separation between physical item inventory status and user work wishlist/intent records during barcode ingestion.

## Requirements

### Requirement: Scan policy mutations target only Item.collection_status
The scanner API SHALL ensure that `ScanBarcodeSchema.policy` field mutations strictly modify `Item.collection_status` and SHALL NOT create, modify, or delete `UserWorkIntent` records.

#### Scenario: Scan with policy changes Item collection status

- **WHEN** a barcode scan request includes `policy: "owned"` for an existing Item
- **THEN** the system SHALL update `Item.collection_status` to `"owned"`
- **AND** no `UserWorkIntent` records SHALL be created or modified

#### Scenario: Scan with policy does not create UserWorkIntent

- **WHEN** a barcode scan request includes `policy: "wishlist"` but the intent is to mark an Item status
- **THEN** the system SHALL update `Item.collection_status` only
- **AND** the system SHALL NOT create a new `UserWorkIntent` record as a side effect

#### Scenario: Policy field validation rejects invalid values

- **WHEN** a barcode scan request includes an unrecognized `policy` value
- **THEN** the system SHALL return a 400 error with validation message
- **AND** no database mutations SHALL occur

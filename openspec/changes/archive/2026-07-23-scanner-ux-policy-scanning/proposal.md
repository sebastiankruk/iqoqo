---
type: Concept
title: proposal
timestamp: 2026-07-22T10:18:48Z
---

## Why

The current scanning flow creates UX friction and rigid data instantiation. First, the scanner forces "book" as the default media type on every new session, frustrating collectors who are scanning batches of CDs or movies and must manually switch the type each time. Second, the backend pipeline assumes that every successful scan must instantiate a physical `Item` inventory record on a shelf. This prevents "policy-based scanning" — where a user wants to catalog a discovery (e.g., adding to a wishlist or library) by creating a `Manifestation` or `UserWorkIntent` *without* asserting physical custody of a copy.

## What Changes

- **Media Type Persistence**: Save the last selected media type in local storage (or React state) during continuous scanning sessions so the UI remembers the collector's current batch context.
- **Policy-Based Scanning Payload**: Modify the scanner submission payload to accept a `policy` intent flag (e.g., `policy: "wishlist"` or `policy: "catalog_only"`).
- **Decoupled Item Instantiation**: Update the backend scanner and resolution controllers to conditionally bypass `Item` creation if the policy dictates non-custodial cataloging, instead linking the user to a `Manifestation` or `UserWorkIntent`.

## Capabilities

### New Capabilities

- `policy-scanning`: Introduces intent-based scanning policies that decouple metadata resolution (creating Works/Expressions/Manifestations) from physical inventory instantiation (Items).
- `scanner-persistence`: Introduces client-side state persistence for batch scanning UX preferences (like media type).

### Modified Capabilities

None — these are new capabilities extending the scanner

## Impact

- **Frontend**: `frontend/components/scanner/` (preserve media type state, add policy toggle in UI).
- **Backend**: `app/api/scanner.py` (accept policy payload, conditionally bypass Item creation logic), `app/core/upc.py` or equivalent resolution logic to handle `UserWorkIntent` linkings.
- **Database**: No strict schema changes, but heavily leverages the existing FRBR entity separation where Manifestations can exist without child Items.

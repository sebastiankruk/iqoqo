---
type: Concept
title: tasks
timestamp: 2026-07-22T10:18:48Z
---

## 1. Frontend: Persistence & Policy UI

- [x] 1.1 In `frontend/components/scanner/index.tsx` (or equivalent parent component), add a `policy` state variable (default `"inventory"`) and a UI toggle/dropdown to select the scanning policy (Inventory, Wishlist, Catalog).
- [x] 1.2 Update the `mediaType` and `policy` state variables to initialize from `localStorage` (`getItem('iqoqo_scanner_media_type')` and `getItem('iqoqo_scanner_policy')`).
- [x] 1.3 Add `useEffect` hooks to synchronize the `mediaType` and `policy` state changes back to `localStorage` (`setItem`).
- [x] 1.4 Update the API submission payload in the scanner component to include the selected `policy`.
- [x] 1.5 Update the success handler in the scanner to display the appropriate success message based on the resolved policy returned by the API (e.g., "Added to Wishlist").

## 2. Backend: API Payload & Validation

- [x] 2.1 In `app/api/scanner.py`, update the `/api/scanner/resolve` (or equivalent) endpoint to accept the `policy` field from the JSON payload. Validate it against allowed values: `["inventory", "wishlist", "catalog"]`.
- [x] 2.2 Update the response formatting logic in `app/api/scanner.py` to handle cases where the resolver returns a `Manifestation` instead of an `Item`, and include the `action` field in the response JSON.

## 3. Backend: Core Resolution Logic

- [x] 3.1 Update the main resolver orchestrator (`app/core/upc.py`, `app/core/isbn.py`, or similar) to accept the `policy` parameter.
- [x] 3.2 Modify the resolver logic to conditionally skip `Item` instantiation. If `policy == 'wishlist'`, create the Work/Expression/Manifestation, then create a `UserWorkIntent` (status `wish_list`).
- [x] 3.3 Modify the resolver logic so if `policy == 'catalog'`, it simply returns the `Manifestation` after creating the core entities without any user linkage.
- [x] 3.4 Ensure the resolver returns the appropriate object (`Manifestation` vs `Item`) based on the executed policy.

## 4. Testing

- [x] 4.1 Write a backend test in `tests/test_api_scanner.py` to verify that scanning with `policy: "wishlist"` creates a `UserWorkIntent` and NO `Item`.
- [x] 4.2 Write a backend test in `tests/test_api_scanner.py` to verify that scanning with `policy: "catalog"` creates NO `Item` and NO `UserWorkIntent`.
- [x] 4.3 Write a frontend test to verify that changing the media type and policy updates `localStorage`.
- [x] 4.4 Run `make lint` and `make test` to ensure everything passes.

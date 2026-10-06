## MODIFIED Requirements

### Requirement: Policy Selection Persistence

The scanner UI SHALL remember the user's last selected scanning policy (Inventory, Wishlist, Catalog) and restore it. The persistence logic SHALL be consolidated to ensure `localStorage` sync occurs in exactly one `useEffect` hook per state variable, eliminating redundant DOM execution and UI jitter. Furthermore, the Policy selection UI SHALL be presented as a floating pill overlaying the camera viewfinder, rather than stacking in the top bar.

#### Scenario: Sequential wishlist scanning

- **WHEN** a user selects the "Add to Wishlist" policy via the floating pill and scans an item
- **THEN** the UI SHALL retain the "Add to Wishlist" policy for the next scan, preventing accidental inventory additions, and the sync to `localStorage` SHALL occur efficiently without duplicated hook executions.

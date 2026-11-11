## MODIFIED Requirements

### Requirement: Ownership Management Filter UI & Single-Item Deep-Link from `/item/[id]`
The `/admin/ownership` UI (`OwnershipManagement` and `OwnershipPage`) SHALL provide localized search and status filter controls using `next-intl` (`AdminOwnership`), hydrate `sourceUserId` and `itemId` from URL query parameters, and `/item/[id]` SHALL render a localized `"Reassign Owner"` (`ItemDetail.reassignOwner`) admin action linking to `/admin/ownership?sourceUserId=<owner_id>&itemId=<item_id>` for users with `transfer:item` permission.

#### Scenario: Admin clicks "Reassign Owner" on `/item/[id]`

- **GIVEN** an authenticated admin or custodian viewing `/item/42` owned by user `u-123` in English or Polish locale
- **WHEN** the user clicks the localized `"Reassign Owner"` button
- **THEN** the browser navigates to `/admin/ownership?sourceUserId=u-123&itemId=42`, automatically selects `u-123` as the source account, filters to item `#42`, pre-checks item `#42` for reassignment preview, and renders all headers and filter controls through `AdminOwnership` translations.

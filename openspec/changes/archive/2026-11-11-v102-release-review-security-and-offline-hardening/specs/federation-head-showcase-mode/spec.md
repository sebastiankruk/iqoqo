## MODIFIED Requirements

### Requirement: Physical Item Write Guard with Wishlist & ActivityPub S2S Preservation
When `FEDERATION_HEAD_MODE` is enabled, the backend SHALL reject local physical `Item` creation (`POST /api/items`, `POST /api/items/manual`, `POST /api/items/bulk`, `POST /api/manifestations/<id>/add`, `POST /api/item/<isbn>` with non-wishlist status, and `POST /api/scan` unless `policy in ("wishlist", "catalog", "catalog_only")` or `collection_status == "wish_list"`) with HTTP `403 Forbidden` and structured JSON `{"error": "...", "code": 403}`, while allowing Wishlist (`UserWorkIntent`) mutations, `GET /api/scanner/preview/<query>`, ActivityPub S2S inbox synchronization (`/ap/inbox`), and admin/custodian metadata curation.

#### Scenario: Authenticated user attempts to add a physical item on Federation Head

- **GIVEN** `FEDERATION_HEAD_MODE` is `true` and a standard authenticated user has a valid session
- **WHEN** the user sends `POST /api/items`, `POST /api/items/manual`, `POST /api/items/bulk`, `POST /api/manifestations/<id>/add`, `POST /api/item/<isbn>`, or `POST /api/scan` with `collection_status="available"`
- **THEN** the server rejects the request with HTTP `403` and JSON `{"error": "This instance operates as a read-only Federation Hub. Physical items are synchronized from connected community nodes; you may still add works to your Wishlist.", "code": 403}` and creates zero `Item` rows.

#### Scenario: Authenticated user adds a work to Wishlist on Federation Head

- **GIVEN** `FEDERATION_HEAD_MODE` is `true` and a user is logged in
- **WHEN** the user creates a wishlist entry via `POST /api/wishlist`, `POST /api/manifestations/<id>/add`, `POST /api/items/bulk`, or `POST /api/scan` with `policy="wishlist"` (`collection_status="wish_list"`)
- **THEN** the server permits the operation (`200`/`201`) without rejecting with `403`.

#### Scenario: Peered community node synchronizes catalog activity to Federation Head

- **GIVEN** `FEDERATION_HEAD_MODE` is `true` and a trusted remote peer sends an HTTP-Signature-verified ActivityPub activity to `/ap/inbox`
- **WHEN** the Federation Head processes the inbound activity
- **THEN** the synchronized `Work`, `Expression`, `Manifestation`, and federated provenance records are ingested normally without being blocked by the local user item write guard.

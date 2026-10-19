## Why
Privacy and consent are fundamental: users must control whether scanned/added items default to public or private, and explicitly opt into federated profile and collection sharing before any data is federated.
## What Changes

- Add `default_item_visibility` (`public` / `private`, default `private`) column to `User` in `app/db/auth.py`.
- Apply `default_item_visibility` automatically during barcode scanning (`/api/scanner`) and manual creation (`/api/items`).
- Expose `/api/v1/profile/federation-consent` endpoint to manage `federated_profile` and `federated_collection` toggles.
- Cherry-pick and adapt `frontend/components/settings/federation-consent.tsx` into `/profile`.
- Trigger actor RSA keypair generation on initial opt-in.

## Capabilities

### New Capabilities
- `user-visibility-defaults-and-consent`: User-level default item visibility settings and profile Federation Consent UI

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

Expands user profile schema and adds UI controls in frontend profile settings.

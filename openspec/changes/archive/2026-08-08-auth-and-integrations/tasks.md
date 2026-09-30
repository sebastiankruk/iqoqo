## 1. Allegro OAuth Backend

- [x] 1.1 Implement API endpoints in `app/api/auth.py` to trigger the Allegro Device Code flow and poll for status
- [x] 1.2 Update `app/utils/allegro.py` to support initiating the device flow and saving tokens from the API context
- [x] 1.3 Add logic to store and securely retrieve Allegro OAuth tokens from the database or token file
- [x] 1.4 Deprecate old SSH token generation script

## 2. Allegro OAuth Frontend

- [x] 2.1 Update `frontend/components/admin/instance-settings.tsx` to include inputs for Client ID/Secret and an "Authorize Allegro" button
- [x] 2.2 Wire the button to get the verification URL and open it in a new tab/window
- [x] 2.3 Display connection status based on the presence of a valid OAuth token

## 3. Twitch Integration Verification

- [x] 3.0 Create Twitch developer account and register application to obtain credentials for local testing
- [x] 3.1 Write unit tests for Twitch API parsing logic using mocked responses
- [x] 3.2 Write integration tests to verify the authentication and error handling flows for Twitch
- [x] 3.3 Execute tests and verify they pass in CI

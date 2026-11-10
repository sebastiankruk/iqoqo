## Context

Once `v1.0.0` lands the Capacitor apps and `v1.0.1` completes the `#v100` domain expansions, the highest-value mobile capability for physical collectors is offline read access to their own catalog when shopping in dead zones.

## Goals / Non-Goals

**Goals:**
- Cache the user's personal collection and wishlist locally on device and serve read-only queries + ISBN/UPC duplicate checks when offline.
- Clear the offline cache immediately upon logout (`clearAllData()`) or server switch so private inventory never leaks across accounts.
- Route notification taps cleanly on mobile.

**Non-Goals:**
- Offline write-queue conflict resolution (mutations require connectivity and display a clear toast when offline).

## Decisions

### Read-Only Cache Cleared on Logout
* **Decision:** Store the serialized collection/wishlist summary keyed by `instanceUrl + userId` and purge it inside `clearAuthToken()` / `clearAllData()`.
* **Rationale:** Guarantees zero cross-account data leakage while providing instant offline search.

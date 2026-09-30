---
type: Concept
title: design
timestamp: 2026-07-22T10:18:48Z
---

## Context

Currently, the scanner component (`frontend/components/scanner/`) initializes with a default media type (usually `"book"`). If a collector is scanning a pile of 50 vinyl records, they must manually switch the type to `"music"` after every single scan because the component state resets.

On the backend, `app/api/scanner.py` passes successful barcode resolutions to `app/core/upc.py` (or ISBN resolver), which resolves the metadata hierarchy (Work → Expression → Manifestation) and *always* creates a physical `Item` record (representing inventory on a shelf). However, some users want to scan a barcode just to log an intent (e.g., "I want to read this book") or to add the metadata to the main catalog without asserting ownership of a physical copy.

## Goals / Non-Goals

**Goals:**

- Persist the selected media type across consecutive scans in the same session.
- Allow the frontend scanner payload to specify an "intent policy" (e.g., `inventory`, `wishlist`, `catalog_only`).
- Modify backend resolution to respect the policy: skip `Item` creation if the policy is not `inventory`.

**Non-Goals:**

- Redesigning the entire scanner UI layout.
- Supporting complex bulk-scan uploads via CSV (this is just for the camera/manual entry scanner).
- Changing the underlying external API resolution logic (Google Books, MusicBrainz, etc.).

## Decisions

### D1: Use LocalStorage for Media Type Persistence

**Decision**: The `MediaTypeSelector` state will be synchronized with `localStorage` (e.g., key `iqoqo_last_scanned_media_type`).

**Rationale**: This ensures that even if the user accidentally refreshes the page or navigates away and back, their batch context is preserved. It's lightweight and requires no backend state.

### D2: Scanner Policy Payload Field

**Decision**: Introduce an optional `policy` field in the POST payload to `/api/scanner/resolve`. Allowed values: `"inventory"` (default), `"wishlist"`, `"catalog"`.

**Rationale**:

- `"inventory"`: Legacy behavior (creates Work → Expr → Manifestation → Item).
- `"wishlist"`: Creates Work → Expr → Manifestation, then creates a `UserWorkIntent` (status = `wish_list`) linked to the Work, skipping `Item`.
- `"catalog"`: Creates Work → Expr → Manifestation, but links nothing to the user.

### D3: Decouple Item Creation in Resolvers

**Decision**: The core resolver functions in `app/core/upc.py` and `app/core/isbn.py` will accept the `policy` parameter and branch their return logic. If `policy != "inventory"`, they return the `Manifestation` object instead of an `Item` object, and handle the `UserWorkIntent` creation if applicable.

**Rationale**: Keeps the branching logic centralized where the FRBR instantiation happens, ensuring all scanner routes (manual, camera, bulk) benefit from the policy feature.

## Risks / Trade-offs

- **[Complex Return Types]** → Mitigation: Resolvers currently return an `Item`. If they return `Manifestation | Item`, API routes must handle the union type gracefully and format the JSON response accordingly.
- **[Cache Invalidation]** → Mitigation: If a scan results in a `wishlist` intent, the frontend must invalidate the `intents` or `wishlist` query cache instead of just the `items` cache.

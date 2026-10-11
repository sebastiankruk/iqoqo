## Context

See `proposal.md` for motivation. Ingest currently stops on the first provider hit. When Google Books returns text metadata without a cover image, Open Library is never queried, stranding the item without cover art.

## Goals / Non-Goals

**Goals:**
- Automatically enrich primary metadata results with missing covers and core bibliographic fields from secondary providers.
- Restrict secondary queries to the exact canonical identifier (ISBN-13 / UPC), avoiding fuzzy title mismatches.
- Record field-level provenance in metadata and RDF `prov:wasDerivedFrom`.
- Enforce strict 3.0s latency ceiling across multi-provider resolution.

**Non-Goals:**
- Fuzzy search cross-matching between different editions or titles.
- Providing an interactive per-field selection UI for custodians (separated into C63 `custodian-provider-merge-ui-v084`).

## Decisions

- **Decision 1: Exact identifier constraint only.**
  - *Rationale:* Only secondary lookups matching the exact same ISBN-13 (or UPC/EAN) are executed for automatic gap-filling. This eliminates the risk of pulling a cover or year from an unrelated edition or translation.
- **Decision 2: Strict immutability of primary fields.**
  - *Rationale:* Primary provider metadata has priority. Secondary attributes only fill fields that are `None` or empty strings.
- **Decision 3: Provenance dictionary in metadata.**
  - *Rationale:* Store `meta["_provenance"] = {"title": "google_books", "cover_url": "open_library"}` so Linked Data serializers attribute sources transparently.

## Risks / Trade-offs

- **[Risk]** Additional network latency on scanner lookups.
  - *Mitigation:* Secondary gap-filling queries run only when core fields (cover or authors) are missing, bounded by a 3.0s total lookup timeout.

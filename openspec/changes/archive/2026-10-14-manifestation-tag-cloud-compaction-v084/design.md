## Context

See `proposal.md` for motivation. Currently, `manifestation-detail-client.tsx` and `item-tabs.tsx` iterate through the `tags` array and render all badges without any limit. When entities have 40+ tags from automated imports, they dominate the vertical viewport.

## Goals / Non-Goals

**Goals:**
- Provide a reusable `<TagCloud tags={tags} maxInitial={10} />` component with "+X more" accordion expansion.
- Track tag provenance source in entity metadata where available (`discogs`, `openlibrary`, `musicbrainz`, `user`).
- Display origin tooltips on tag chips.

**Non-Goals:**
- Rebuilding the global tag taxonomy database architecture.

## Decisions

- **Decision 1: Client-side folding with state toggle**
  - *Rationale*: All tags are already in the initial JSON response; folding client-side avoids extra network requests and feels instantaneous.

## Risks / Trade-offs

- **[Risk]** Existing entities lack granular source metadata for historical tags.
  - **Mitigation**: Default to "Source: Catalog Ingestion" when source provider is unspecified.

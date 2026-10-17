## Why

As iqoqo expands from isolated single-instance home labs into a federated network of physical media collectors, two crucial capabilities are needed across the `v0.9.x` lifecycle:
1. **Top/Read-Only Index Instance of Connected Libraries:** Instance administrators and public collectors need an aggregator / discovery mode where an instance can act as a top-level read-only directory indexing connected federated libraries, their public collections, and instance statistics.
2. **In-App End-User Documentation:** As federation, LOD linking, and FRBR curation workflows grow in sophistication, everyday collectors need accessible, in-app documentation explaining concepts (e.g. Work vs Expression vs Manifestation, federated loans, ActivityPub handles, and LOD linking) directly inside the iqoqo web interface rather than relying exclusively on external GitHub markdown docs.

## What Changes

- Introduce a configuration mode (`INSTANCE_ROLE=directory` or `INSTANCE_ROLE=catalog`) enabling an instance to operate in an aggregated, read-only discovery mode indexing known peer libraries discovered via the Trust Graph.
- Create an in-app documentation viewer and knowledge hub (`/help` or `/docs` frontend route with interactive search) rendering user-friendly guides on cataloging, scanning, federation, and sharing.
- Package localized help articles (`pl`, `en`) explaining physical media categorization and federation privacy models.

## Capabilities

### New Capabilities
- `federated-directory-index`: Aggregated read-only directory view of known peer libraries and their public statistics.
- `in-app-user-documentation`: Integrated end-user documentation and guide system within the Next.js frontend.

## Impact

- Affects frontend routing (`frontend/app/docs/` or `frontend/app/help/`) and discovery endpoints.
- Provides accessible onboarding for collectors and multi-node discovery across instances.

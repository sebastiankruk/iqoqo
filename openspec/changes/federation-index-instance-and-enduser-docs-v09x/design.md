## Context

As iqoqo grows into a decentralized network, two usability gaps emerge:
1. Collectors want to find other public libraries in the fediverse without guessing domains.
2. Collectors need clear explanations of library-grade concepts (FRBR Works, Expressions, Manifestations, physical inventory tags, ActivityPub handles) directly inside the UI without leaving the app.

## Goals / Non-Goals

**Goals:**
- Provide a directory view aggregating public library metadata from the `FederationInstance` Trust Graph.
- Build a lightweight in-app documentation viewer using Next.js Server Components and MDX/markdown.

**Non-Goals:**
- Creating a centralized global tracker that breaks decentralization.
- Permitting arbitrary user markdown uploads without sanitization.

## Decisions

### 1. Leverage Existing Trust Graph (`FederationInstance`)
- **Decision:** Drive directory data directly from `FederationInstance` records with `trust_level IN ('trusted', 'verified')`.
- **Rationale:** Avoids a separate database table; reuses peer discovery and periodic health checks from `C77`.

### 2. Static Content with Locale Fallbacks for Help Docs
- **Decision:** Author user-facing documentation articles in frontend content bundles with dynamic locale loading (`/messages/docs/en/*.md` and `/messages/docs/pl/*.md`).
- **Rationale:** Ensures fast client-side rendering without external database dependencies.

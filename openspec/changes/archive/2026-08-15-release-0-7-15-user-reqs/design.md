## Context

Users want a way to submit feedback directly from the app. Additionally, the faceted navigation lacks an intuitive way for users to discover what they _don't_ own within a filtered category.

## Goals / Non-Goals

**Goals:**

- Provide a UI and API endpoint to collect user feedback.
- Enhance the faceted navigation system to support inverse ownership filtering ("not in my collection").

**Non-Goals:**

- Building a full customer support ticketing system.
- Completely rewriting the faceted search engine.

## Decisions

- **Feedback Mechanism**: A modal triggered from a single "Help & Feedback" entry in the user profile dropdown menu that submits data to a new `/api/feedback` endpoint. The data will be stored in a new database table locally so it can be managed within the app and exported as RDF/JSON-LD.
  - Upon submission, the modal transitions to a clear Success State (hiding the form) and the submit button becomes a "Close" button.
  - User should be able to specify whether this is a Feature Request or a Bug, and attach multiple screenshots.
  - Admin and User should see tickets on a new full-page screen with standard Navbar/Footer navigation, left-side filtering, pagination, and enhanced ticket cards (status badges, comment counts, attachment counts).
  - Screenshot attachments are served directly through Nginx `/static/gallery/` and `/api/static/gallery/` without 404s.
  - Role-Based Access Control (RBAC):
    - Admins (`tickets:admin`) can see requester identity, change ticket status, leave comments, and interact with all tickets.
    - Ticket Creators (`tickets:creator`) can view details, leave comments, and close their own tickets.
- **Ownership Filter**: A new explicit facet category called "Ownership" with options like "Owned" and "Not Owned". This instructs the backend to perform the appropriate joins against the user's collection to filter by ownership status. This facet is hidden/removed when in the Items view, as it only applies to higher-level FRBR entities (Manifestations, Expressions, Works). Default unselected state preserves full catalog visibility.
- **Testing & Quality Shield**: Strict multi-tier testing encompassing:
  - Backend integration tests for ownership join queries and feedback lifecycle (`pytest`).
  - Frontend component tests for feedback modal interfaces (`vitest`).
  - End-to-end browser workflows verifying filter empty states and ticket submission (`playwright`).

## Risks / Trade-offs

- [Risk] Feedback endpoint could be spammed. → Mitigation: Apply strict rate limiting on the `/api/feedback` route.
- [Risk] Inverse search queries might be slow on large catalogs. → Mitigation: Ensure `Item` ownership indexes are optimized for anti-joins.

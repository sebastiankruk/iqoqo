## 1. Feedback Mechanism

- [x] 1.1 Create new DB table for Feedback items (with status, type, and relationships).
- [x] 1.2 Create new backend endpoint `/api/feedback` with rate limiting and file upload support for screenshots.
- [x] 1.3 Add frontend feedback modal UI accessible from user profile dropdown menu.
- [x] 1.4 Add a new Feedback management screen to list and filter tickets for Users and Admins.
- [x] 1.5 Connect frontend UI to backend endpoints.
- [x] 1.6 Consolidate profile dropdown entries into a single "Help & Feedback" link.
- [x] 1.7 Redesign feedback submission success state to hide the form and display a prominent success message with a "Close" button.
- [x] 1.8 Enhance ticket list item cards (add status badge, comment count, attachment count, truncated description).
- [x] 1.9 Refactor Feedback management into a dedicated full-page screen with left-side filtering and pagination.
- [x] 1.10 Implement Role-Based Access Control (RBAC) views for tickets (Admin vs. Creator) and ensure Admins can click and interact with tickets from the list.
- [x] 1.11 Add new permission scopes `tickets:admin` and `tickets:creator`, assigning the former to the Admin role and the latter to the regular user role as defaults.

## 2. Faceted Navigation

- [x] 2.1 Add an "Ownership" facet category with "Owned" and "Not Owned" options in the UI.
- [x] 2.2 Update search API payload to accept ownership facet filters.
- [x] 2.3 Implement joins in the backend search query to handle the "Owned" and "Not Owned" conditions.
- [x] 2.4 Ensure "OWNERSHIP" facet correctly calculates and shows "Owned" and "Not Owned" options.
- [x] 2.5 Remove or hide the "OWNERSHIP" filter entirely when in the Items view.
- [x] 2.6 Ensure unselected ownership filter defaults to showing both owned and unowned items, correctly inferring ownership across Works, Expressions, and Manifestations.

## 3. Infrastructure, Layout & Test Coverage

- [x] 3.1 Embed standard application Header (Navbar) and Footer on the Feedback management page.
- [x] 3.2 Configure Nginx static gallery routing and frontend image resolver to serve feedback attachments without 404s.
- [x] 3.3 Add unit and integration tests for feedback API lifecycle, status updates, and ownership filtering (`pytest`).
- [x] 3.4 Add frontend component tests with TypeScript strictness for feedback modals (`vitest`).
- [x] 3.5 Add Playwright E2E tests for Ownership filter drawer defaults and Feedback ticket submission workflow.

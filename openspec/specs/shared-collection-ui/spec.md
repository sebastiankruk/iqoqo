# shared-collection-ui Specification

## Purpose
TBD - created by archiving change clean-shared-collection-ui. Update Purpose after archive.
## Requirements
### Requirement: Global Navigation in Shared View

The system SHALL ensure that public shared collection pages provide global site navigation elements (Navbar, Footer) to maintain context and continuity for unauthenticated users.

#### Scenario: Unauthenticated user views shared collection

- **WHEN** an unauthenticated user navigates to a `/share/[token]` link
- **THEN** the page renders the shared collection along with the global site Navbar and Footer components, without triggering redirection or 401 errors.


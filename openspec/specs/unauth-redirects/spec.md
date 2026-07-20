# unauth-redirects Specification

## Purpose

TBD - created by archiving change fix-unauth-redirects. Update Purpose after archive.

## Requirements

### Requirement: Redirect Unauthenticated Access

The system SHALL redirect unauthenticated users to the login page when they attempt to access protected routes, rather than returning a 404 error.

#### Scenario: Unauthenticated user accesses shared wishlist

- **WHEN** an unauthenticated user accesses a URL for a protected wishlist or collection
- **THEN** the system redirects the user to the login page
- **AND** ideally preserves the intended destination for post-login redirection.

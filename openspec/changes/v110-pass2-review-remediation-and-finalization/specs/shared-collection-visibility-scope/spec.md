## MODIFIED Requirements

### Requirement: Token Scope + Friend Bonus Resolution Across All Share Outputs
All shared collection delivery surfaces (`GET /api/public/share/<token>`, `GET /share/<token>`, `GET /share/<token>/jsonld/<page>`, `GET /api/public/rdf/share/<token>`, and RSS feeds) SHALL resolve visible items using the Token Scope + Friend Bonus model, set `Cache-Control: private, no-store` whenever authenticated friend bonus or non-public scopes (`friends_and_public`, `all`) are served, and enforce strict `is_hidden = FALSE` privacy isolation whenever full-text or `ILIKE` search is executed with `include_hidden=False`.

#### Scenario: `public_only` share excludes non-public items for anonymous visitors and grants Friend Bonus to authenticated friends

- **GIVEN** User A creates a `SharedCollection` with `visibility_scope="public_only"` over items including `public`, `friends_only`, and `private` copies
- **WHEN** an anonymous visitor or non-friend requests the share link (web, JSON, JSON-LD, or RSS)
- **THEN** only `public` items MUST be returned.
- **WHEN** an accepted friend User B (or User A) requests the share link with valid authentication credentials
- **THEN** both `public` and `friends_only` items MUST be returned (with `private` still excluded), and `Cache-Control` MUST NOT allow shared public caching.

#### Scenario: `friends_and_public` share reveals `friends_only` items to token holders while hiding `private`

- **GIVEN** User A creates a `SharedCollection` with `visibility_scope="friends_and_public"`
- **WHEN** any caller (authenticated or anonymous, including AI fetchers) requests the share link with the valid 256-bit `share_token`
- **THEN** matching `public` and `friends_only` items MUST be included, and `private` items MUST remain excluded.

#### Scenario: `all` share reveals all matching owner items (`public`, `friends_only`, `private`) to token holders

- **GIVEN** User A creates a `SharedCollection` with `visibility_scope="all"`
- **WHEN** any caller requests the share link with the valid 256-bit `share_token`
- **THEN** matching `public`, `friends_only`, and `private` items owned by User A MUST be included across JSON, SSR HTML, JSON-LD/Turtle, and RSS outputs.

#### Scenario: Owner-scoped search with `include_hidden=False` never returns `private` or `friends_only` items

- **GIVEN** User A owns `public` (`is_hidden=False`), `friends_only` (`is_hidden=True`), and `private` (`is_hidden=True`) items matching query `"Dune"`
- **WHEN** item search executes for `user_id=User A` with `owner_only=True` and `include_hidden=False` (without an explicit non-public `visibility` list)
- **THEN** only User A's `public` (`is_hidden=False`) items MUST be returned, and `friends_only` and `private` items MUST be excluded.

#### Scenario: Query-filtered `friends_and_public` or Friend Bonus share includes matching `friends_only` items across JSON and RDF

- **GIVEN** User A creates a `SharedCollection` with `filters={"query": "Dune", "visibility_scope": "friends_and_public"}` (or `public_only` viewed by accepted friend User B) over a `public` item and a `friends_only` (`is_hidden=True`) item matching `"Dune"` plus a `private` item matching `"Dune"`
- **WHEN** the share collection is fetched via `GET /api/public/share/<token>` or `fetch_shared_collection_by_token()`
- **THEN** both the matching `public` and `friends_only` items MUST be returned while the `private` item and any hidden-public item (`visibility="public", is_hidden=True`) remain excluded.

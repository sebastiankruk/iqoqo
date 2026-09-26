# security/hardening-v081 Specification

## Purpose

Defines security hardening requirements for the iqoqo application addressing 29 in-scope moderate security findings across credential validation, input sanitization, database constraints, rate limiting, token caching, SSRF prevention, and deployment defaults. Account-deletion confirmation (`MOD-SEC-22`) is deferred to the dedicated v0.8.3 change `account-deletion-email-confirmation-v083`.

## Requirements

### Requirement: Minimum Password Length and Registration Validation
The authentication service SHALL reject registration and password update requests with passwords shorter than 8 characters, and the administrative user initialization utility SHALL enforce the same minimum length and reject empty credentials.

#### Scenario: User registers with a password shorter than 8 characters

- **WHEN** a user attempts to register with a password of length 7 or fewer characters
- **THEN** the API returns HTTP 400 Bad Request with a clear validation error message stating passwords must be at least 8 characters long

#### Scenario: User registers with a valid password

- **WHEN** a user registers with a password of 8 or more characters
- **THEN** the system hashes the password securely and creates the user account

#### Scenario: Admin initialization with empty password

- **WHEN** the `init_auth.py` script executes with an empty or whitespace-only password
- **THEN** the script aborts immediately with an error and refuses to create an administrator account

### Requirement: User Account Credential Constraint
The database schema SHALL enforce that every user account has at least one valid authentication mechanism: either a non-null `password_hash` or a non-null `google_id`.

#### Scenario: Insert user with neither password nor OAuth identity

- **WHEN** a database insert or update attempts to persist a user row where both `password_hash` and `google_id` are NULL
- **THEN** PostgreSQL raises a CheckConstraint violation and rejects the transaction

#### Scenario: Insert user with OAuth identity only

- **WHEN** a user is provisioned via Google OAuth with a non-null `google_id` and null `password_hash`
- **THEN** the database transaction succeeds

### Requirement: One-Time Authorization Code Exchange
OAuth authentication flows SHALL avoid transmitting persistent JSON Web Tokens directly in URL query parameters or browser redirect fragments, instead utilizing a short-lived, single-use authorization code exchanged via a secure HTTP POST request.

#### Scenario: OAuth callback completes

- **WHEN** a third-party OAuth provider redirects back to the application callback
- **THEN** the backend redirects to the frontend with an ephemeral authorization code in the body or payload, not the permanent JWT token in query parameters

#### Scenario: Exchanging authorization code for session tokens

- **WHEN** the frontend submits the one-time authorization code via HTTP POST
- **THEN** the backend validates and consumes the code, returning the authentication tokens and invalidating the code against reuse

### Requirement: Active User Status Verification for Admin Tokens
The administrative token generator utility SHALL verify that the target user account has `is_active = True` before generating and outputting an administrative JWT bearer token.

#### Scenario: Generating token for deactivated user

- **WHEN** an operator attempts to generate an administrative token for an account marked as inactive or suspended
- **THEN** the utility halts with an error and refuses to issue a token

### Requirement: Client Error Message Sanitization
The API SHALL sanitize all authentication and catalog error messages returned to clients, ensuring internal exception tracebacks, system internals, and sensitive identifier strings like ISBN query terms are omitted from error payloads.

#### Scenario: Manifestation lookup failure

- **WHEN** an external provider query fails during an ISBN lookup request
- **THEN** the API returns a generic descriptive error message without echoing raw internal exception traces or unescaped query arguments

#### Scenario: OAuth handshake error

- **WHEN** an error occurs during third-party OAuth token exchange
- **THEN** the system logs the full technical diagnostic details internally and returns a sanitized user-friendly error to the client

### Requirement: User Content Sanitization via Bleach
All user-generated free text (including social notes, reviews, feedback descriptions, and comments) SHALL be sanitized at API ingress using `bleach.clean(tags=[], attributes={}, protocols=[], strip=True)` to eliminate XSS injection vectors.

#### Scenario: User submits note containing HTML markup or script injection

- **WHEN** a user posts a note or feedback comment containing `<script>alert('xss')</script>` or other HTML tags
- **THEN** the system strips all HTML tags and stores only the plain text content

#### Scenario: User submits plain text content with punctuation

- **WHEN** a user posts text containing standard punctuation like `5 < 10 and 10 > 5`
- **THEN** the content is safely preserved without tag distortion or stripping of legitimate text

### Requirement: Avatar Protocol Validation and SSRF Prevention
The user profile API SHALL accept only safe `https://` URLs for `avatar_url` submissions and SHALL block other schemes and internal loopback, link-local, or cloud metadata IP addresses.

#### Scenario: Submitting unsafe URI schemes as avatar URL

- **WHEN** a user submits an `avatar_url` with schemes like `javascript:`, `data:`, or `file:`
- **THEN** the API rejects the request with HTTP 400 Bad Request

#### Scenario: Submitting a plaintext HTTP or relative avatar URL

- **WHEN** a user submits an `avatar_url` using `http://` or a relative path
- **THEN** the API rejects the request with HTTP 400 Bad Request

#### Scenario: Submitting SSRF loopback or metadata endpoints

- **WHEN** a user submits an avatar URL targeting `127.0.0.1`, `localhost`, or AWS/cloud metadata address `169.254.169.254`
- **THEN** the API blocks the request with HTTP 400 Bad Request

#### Scenario: Submitting a valid HTTPS external image URL

- **WHEN** a user submits a publicly accessible HTTPS image URL
- **THEN** the profile is updated with the valid avatar URL

### Requirement: External Query Parameter Injection Prevention
External provider API query builders, including IGDB and MusicBrainz clients, SHALL sanitize user input by stripping and escaping backslashes before escaping quotes to prevent query injection.

#### Scenario: Searching IGDB with quotes and backslashes

- **WHEN** a search query containing quotes, backslashes, or control characters is passed to the IGDB query builder
- **THEN** the client properly escapes all special characters and constructs a syntactically valid search string without payload injection

### Requirement: Full-Text Search Schema Allowlist Enforcement
The search service SHALL strictly validate schema prefixes against a hardcoded allowlist (`catalog` or `inventory`) before constructing dynamic SQL queries, refusing arbitrary or untrusted schema names.

#### Scenario: Dynamic search query initialization

- **WHEN** full-text search queries are initialized with configured schema prefixes
- **THEN** the service validates that the prefix matches approved schema constants and aborts if an unexpected schema string is encountered

### Requirement: Database Lifecycle and Visibility Check Constraints
Database tables for users, items, and intents SHALL enforce valid enum values at the database schema level using PostgreSQL CheckConstraints.

#### Scenario: Invalid User visibility value

- **WHEN** an INSERT or UPDATE on `auth.users` specifies a visibility other than `'private'`, `'shared'`, or `'public'`
- **THEN** PostgreSQL rejects the transaction with a CheckConstraint error

#### Scenario: Invalid Item status or collection_status

- **WHEN** an INSERT or UPDATE on `inventory.items` specifies a status outside the recognized item lifecycle states
- **THEN** PostgreSQL rejects the transaction with a CheckConstraint error

#### Scenario: Invalid UserWorkIntent status

- **WHEN** an INSERT or UPDATE on `inventory.user_work_intents` specifies an invalid intent status
- **THEN** PostgreSQL rejects the transaction with a CheckConstraint error

### Requirement: Lending Self-Borrow Prevention
The lending API, frontend, and database SHALL prohibit users from creating loan requests for items they already own. The database SHALL enforce this cross-table invariant independently of API validation.

#### Scenario: User requests loan for their own item

- **WHEN** an authenticated user creates a loan request for an item where `item.owner_id == current_user.id`
- **THEN** the API returns HTTP 400 Bad Request and no loan request record is created

#### Scenario: Direct database write attempts a self-borrow

- **WHEN** a database insert or update attempts to create a loan request whose requester is the associated item's owner
- **THEN** the database rejects the write and no loan request record is created

#### Scenario: Owner views their own item in the lending UI

- **WHEN** an item owner views the lending controls for their own item
- **THEN** the UI does not offer an actionable request-to-borrow control, and any server-side rejection is presented clearly

### Requirement: Polymorphic Association and Container Constraints
Database tables supporting polymorphic relationships SHALL enforce structural integrity constraints via PostgreSQL CheckConstraints.

#### Scenario: Roadmap item target integrity

- **WHEN** an INSERT or UPDATE on `RoadmapItem` specifies no target or more than one of `work_id`, `expression_id`, and `manifestation_id`
- **THEN** PostgreSQL rejects the transaction with a CheckConstraint error

#### Scenario: Expression-only roadmap target

- **WHEN** a roadmap item specifies exactly one target, `expression_id`
- **THEN** PostgreSQL accepts the item; expression-only targets remain supported

#### Scenario: Item-level roadmap target

- **WHEN** a client requests Item-level roadmap targeting
- **THEN** this change does not add that capability; it is deferred to the v0.8.3 roadmap change

#### Scenario: Container aggregation with invalid target type

- **WHEN** a `ContainerAggregation` record is inserted with an `aggregated_type` not in `('work', 'item')`
- **THEN** PostgreSQL rejects the transaction with a CheckConstraint error

### Requirement: Eager Loading in Catalog List Views
Catalog and collection list view API endpoints SHALL eagerly load related entities (`Manifestation.author` and `Work.expressions`) using joined loads or select-in loads, preventing N+1 query storms and unauthorized data traversal leaks.

#### Scenario: Listing catalog items with manifestations

- **WHEN** a client requests a paginated list of catalog works or manifestations
- **THEN** all associated authors and child expressions are retrieved in batched queries without individual per-row database roundtrips

### Requirement: Public Endpoint Rate Limiting
Publicly accessible and unauthenticated endpoints, including RSS feeds (`/api/public/feed.xml`), user directory searches, and collection share token creation, SHALL enforce explicit rate limits.

#### Scenario: Client exceeds RSS feed rate limit

- **WHEN** a client makes more than 60 requests per minute to `/api/public/feed.xml`
- **THEN** the API responds with HTTP 429 Too Many Requests

#### Scenario: User searches profiles rapidly

- **WHEN** an authenticated user exceeds 30 profile search requests per minute on `/api/profile/search`
- **THEN** the API responds with HTTP 429 Too Many Requests

#### Scenario: Rapid collection share link generation

- **WHEN** a user exceeds 30 share generation requests per minute on `/api/sharing`
- **THEN** the API responds with HTTP 429 Too Many Requests

### Requirement: Redis-Cached Token Revocation Check
The authentication interceptor SHALL query a Redis key-value cache before querying PostgreSQL to check if a bearer token has been blocklisted, and SHALL fall back to PostgreSQL if Redis is unavailable or unpopulated.

#### Scenario: Authenticated request with valid token

- **WHEN** an authenticated request arrives with a valid JWT
- **THEN** the system checks Redis for the token JTI; upon finding no entry, authentication proceeds without hitting the database

#### Scenario: Request with revoked token

- **WHEN** a request arrives using a previously revoked bearer token
- **THEN** the revocation status is identified via Redis cache and the request is immediately rejected with HTTP 401 Unauthorized

### Requirement: Social Feedback and System Stats Access Protections
Public social feedback and notes endpoints SHALL support `@optional_auth` to populate user context when present, and unauthenticated administrative stats endpoints SHALL be documented and rate-limited.

#### Scenario: Unauthenticated client requests social feedback

- **WHEN** an unauthenticated client queries `/api/feedback/<level>/<target_id>`
- **THEN** the API returns the public social feedback items with current user actions set to false

#### Scenario: Authenticated user queries social feedback

- **WHEN** an authenticated user queries `/api/feedback/<level>/<target_id>`
- **THEN** the API returns the feedback items annotated with the user's specific vote and ownership states

#### Scenario: Unauthenticated access to global stats

- **WHEN** a client queries the existing public endpoint `/api/stats/global`
- **THEN** the request is rate-limited and returns only high-level aggregate counts without personal or sensitive instance metadata

#### Scenario: Global stats query failure

- **WHEN** a database error prevents loading global statistics
- **THEN** the client receives a generic error response while diagnostic details are logged internally

### Requirement: Secure Permissions for Cached Credentials
Files written to local or container filesystems containing external API credentials or session tokens, such as cached IGDB tokens, SHALL be written with strict POSIX file permissions of `0o600` (read/write by owner only).

#### Scenario: Caching IGDB authentication token

- **WHEN** the external service client writes the retrieved IGDB OAuth token to disk
- **THEN** the file is created with file mode `0o600` preventing other system users or containers from reading the credentials

### Requirement: Shared Collection Error Differentiation and Current Next.js Runtime Conventions
The shared collection frontend interface SHALL differentiate between HTTP 404 (non-existent share token) and HTTP 50x (server error). The application SHALL retain its active Next.js 16 `proxy.ts` page-routing behavior and tests, while generated metadata routes SHALL not opt into the deprecated Edge Runtime.

#### Scenario: Shared collection token does not exist

- **WHEN** a visitor navigates to a shared collection URL with an invalid or expired token resulting in HTTP 404
- **THEN** the UI renders a "Collection Not Found or Expired" notice

#### Scenario: Server error loading shared collection

- **WHEN** the backend returns HTTP 500 when fetching a shared collection
- **THEN** the UI renders a "Server Error - Please Try Again Later" alert rather than falsely reporting the collection is missing

#### Scenario: Protected page routing remains covered

- **WHEN** the frontend proxy tests execute for protected routes
- **THEN** `frontend/proxy.ts` continues redirecting unauthenticated page requests to login; this UI routing behavior does not replace backend authorization

#### Scenario: Apple icon uses the default Node.js runtime

- **WHEN** the frontend is built and the generated `/apple-icon` route is requested
- **THEN** build/startup output contains no Edge Runtime deprecation warning and the route returns a rendered PNG image

### Requirement: Production Deployment Defaults and Secret Safeguards
Container definitions and environment templates SHALL enforce secure-by-default configurations, requiring explicit database passwords in production, failing fast on insecure secret keys, and disabling optional LLM features by default.

#### Scenario: Container startup in production with default database credentials

- **WHEN** `docker-compose.yml` or container services launch in a production environment
- **THEN** the services require an explicit `POSTGRES_PASSWORD` from `.env` and refuse to boot with default `changeme` passwords

#### Scenario: Application startup with insecure default secret key

- **WHEN** the Flask application starts with `FLASK_ENV=production` and `SECRET_KEY` matches known default or placeholder values
- **THEN** the application throws a fatal configuration exception and refuses to bind network sockets

#### Scenario: Default configuration for LLM integrations

- **WHEN** a new deployment environment is configured using `.env.example`
- **THEN** `ALLOW_LLM` defaults to `false` to avoid unexpected billing or unauthenticated model invocation

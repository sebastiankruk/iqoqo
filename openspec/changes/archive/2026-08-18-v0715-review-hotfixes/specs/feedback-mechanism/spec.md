## MODIFIED Requirements

### Requirement: Feedback Rate Limiting

The feedback API SHALL restrict the number of submissions per user to prevent spam. Additionally, all feedback read and update endpoints SHALL enforce per-user rate limits to prevent denial-of-service via rapid paginated queries or status mutations.

#### Scenario: Exceeding rate limit on submission

- **WHEN** a user submits more than 5 feedback reports in an hour
- **THEN** the API returns a 429 Too Many Requests response.

#### Scenario: Exceeding rate limit on listing

- **WHEN** a user issues more than 60 GET requests to `/api/feedback` or `/api/feedback/<id>` within one minute
- **THEN** the API returns a 429 Too Many Requests response.

#### Scenario: Exceeding rate limit on updates

- **WHEN** a user issues more than 30 PATCH requests to `/api/feedback/<id>` within one minute
- **THEN** the API returns a 429 Too Many Requests response.

## ADDED Requirements

### Requirement: Feedback Upload File Count Limit

The feedback submission endpoint SHALL enforce a maximum of 5 screenshot attachments per ticket to prevent storage and memory exhaustion attacks.

#### Scenario: Exceeding file upload limit

- **WHEN** a user submits a feedback ticket with more than 5 screenshot files attached
- **THEN** the API returns HTTP 400 with the message "Maximum 5 screenshots allowed per ticket" and no files are persisted.

### Requirement: Pagination Parameter Clamping

The feedback listing endpoint SHALL clamp `page` and `per_page` query parameters to positive integers, preventing negative SQL OFFSET/LIMIT errors.

#### Scenario: Negative page parameter

- **WHEN** a client sends `GET /api/feedback?page=-1`
- **THEN** the API treats `page` as 1 and returns the first page of results.

#### Scenario: Excessive per_page parameter

- **WHEN** a client sends `GET /api/feedback?per_page=500`
- **THEN** the API clamps `per_page` to 100 and returns at most 100 results.

### Requirement: Closed Ticket Comment Guard

The feedback update endpoint SHALL reject comment additions to tickets with status `closed`, preventing unbounded JSONB array growth on archived records.

#### Scenario: Commenting on a closed ticket

- **WHEN** a user or admin sends a PATCH request with a non-empty `comment` field to a ticket whose status is `closed`
- **THEN** the API returns HTTP 400 with the message "Cannot add comments to a closed ticket" and the comment is not persisted.

### Requirement: Feedback Attachment Display

Feedback screenshot thumbnails SHALL preserve the original aspect ratio of uploaded images, using `object-contain` instead of `object-cover` to prevent cropping vertical mobile screenshots.

#### Scenario: Viewing a vertically-oriented screenshot

- **WHEN** a user or admin views a feedback ticket containing a vertically-oriented (portrait) mobile screenshot
- **THEN** the full image is visible within the thumbnail container without cropping, using letterboxing if necessary.

### Requirement: Nginx Payload Alignment

The reverse proxy configuration SHALL set `client_max_body_size` to at least 50M to match the backend's per-file (10MB) × max-files (5) upload validation, preventing silent 413 rejection of legitimate feedback submissions.

#### Scenario: Uploading maximum-sized attachments

- **WHEN** a user submits a feedback ticket with 5 screenshots, each approaching 10MB
- **THEN** the Nginx proxy accepts the request and forwards it to the Flask backend for validation.

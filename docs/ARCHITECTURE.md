# iqoqo Architecture Guide

## 🏛️ Core Philosophy: FRBR-First Design

iqoqo is built on the **Functional Requirements for Bibliographic Records (FRBR)** model, specifically the FRBRoo (object-oriented) variant. This architecture ensures that bibliographic data is properly structured, deduplicated, and semantically meaningful.

## 📚 The FRBR Hierarchy

Every item in iqoqo exists within a strict four-tier hierarchy:

```text
Work (Concept)
  └── Expression (Version)
      └── Manifestation (Edition)
          └── Item (Physical/Digital Copy)
```

### 1. Work - The Abstract Concept

**Database**: `works` table

A Work represents the **abstract intellectual or artistic creation** - the story, the composition, the idea itself, independent of any particular realization.

**Example**: "The Hobbit" as a story concept

**Attributes**:

- `title` - The work's title
- `meta` - JSON containing:
  - `authors` - List of author names
  - `categories` - Subject classifications
  - `original_language` - Language of original creation

**Key Principle**: Multiple editions/translations of the same intellectual work share **one** Work entity.

```python
# One Work for all editions and translations
work = Work(
    title="The Hobbit",
    meta={
        "authors": ["J.R.R. Tolkien"],
        "categories": ["Fantasy", "Adventure"],
        "original_language": "en"
    }
)
```

### 2. Expression - The Specific Version

**Database**: `expressions` table

An Expression represents a **specific intellectual realization** of a Work - a particular text, translation, adaptation, or performance.

**Examples**:

- The English text of "The Hobbit"
- The German translation "Der Hobbit"
- The audiobook narration by Rob Inglis

**Attributes**:

- `work_id` - Foreign key to Work
- `content_type` - Type of content: 'text', 'audio', 'video', etc.
- `language` - ISO language code (e.g., 'en', 'de', 'pl')
- `meta` - JSON for additional expression-level data

**Key Principle**: Each language/format combination gets its own Expression, but they all point to the same Work.

```python
# English text expression
expression_en = Expression(
    work_id=work.id,
    content_type="text",
    language="en"
)

# German translation expression
expression_de = Expression(
    work_id=work.id,
    content_type="text",
    language="de"
)
```

### 3. Manifestation - The Physical/Digital Edition

**Database**: `manifestations` table

A Manifestation represents a **physical or digital embodiment** of an Expression - a specific published edition with its own ISBN, publisher, publication date, and physical characteristics.

**Examples**:

- 1937 Allen & Unwin hardcover first edition (ISBN: 9780048230706)
- 2012 Del Rey mass market paperback (ISBN: 9780345534835)
- 2020 Mariner Books illustrated edition (ISBN: 9780358653035)

**Attributes**:

- `expression_id` - Foreign key to Expression
- `isbn13` - ISBN-13 identifier (unique)
- `upc` - Universal Product Code
- `ean` - European Article Number
- `publisher` - Publisher name
- `publication_date` - Date of publication
- `meta` - JSON containing:
  - `imageLinks` - Cover image URLs
  - `pageCount` - Number of pages
  - `dimensions` - Physical size
  - `industryIdentifiers` - Other IDs

**Key Principle**: Each distinct ISBN represents a separate Manifestation, even if it's the "same book."

```python
# 1937 first edition
manifestation_1937 = Manifestation(
    expression_id=expression_en.id,
    isbn13="9780048230706",
    publisher="Allen & Unwin",
    publication_date=date(1937, 9, 21),
    meta={
        "pageCount": 310,
        "imageLinks": {"thumbnail": "..."}
    }
)

# 2012 paperback reprint
manifestation_2012 = Manifestation(
    expression_id=expression_en.id,
    isbn13="9780345534835",
    publisher="Del Rey",
    publication_date=date(2012, 1, 1)
)
```

### 4. Item - The Specific Copy

**Database**: `items` table

An Item represents **your specific copy** - the physical book on your shelf or the digital file you own, with its unique characteristics like condition, notes, and location.

**Examples**:

- The copy on your bookshelf with a coffee stain on page 47
- Your signed first edition
- Your Kindle version with highlights

**Attributes**:

- `manifestation_id` - Foreign key to Manifestation
- `owner_id` - User who owns this copy
- `status` - 'available', 'lent', 'lost', 'wish_list', 'reading', 'read'
- `condition` - 'new', 'like_new', 'good', 'fair', 'poor'
- `added_at` - When added to collection
- `meta` - JSON for user-specific data:
  - `notes` - Personal notes
  - `tags` - Custom tags
  - `location` - Shelf location
  - `purchase_date` - When acquired
  - `purchase_price` - What you paid

**Key Principle**: Multiple users can own the same Manifestation, but each has their own Item record.

```python
# Your specific copy
item = Item(
    manifestation_id=manifestation_2012.id,
    owner_id="user123",
    status="available",
    condition="good",
    meta={
        "notes": "Gift from Mom, 2023",
        "location": "Living room bookshelf, 3rd shelf",
        "tags": ["favorites", "fantasy"]
    }
)
```

### Virtual Wishlist Items (`UserWorkIntent`)

Wishlist items that do not yet have a specific physical copy (Item record) are represented as **virtual items** backed by the `UserWorkIntent` model.

- **Negative IDs**: In API responses and UI grids, virtual items use negative integer IDs (`-1`, `-2`, etc.) derived from the `UserWorkIntent` record to distinguish them from persistent physical `Item` records.
- **FRBR Tier**: `UserWorkIntent` models a user's intent or wish regarding a `Work` or `Manifestation` without instantiating an owned physical item copy.
- **Virtual-to-Physical Transition**: When a user modifies a virtual item (e.g., adding tags, setting shelf location, or changing condition), the backend automatically converts the `UserWorkIntent` into a true physical `Item` record with status `wish_list`, assigning a positive integer database primary key.

## 🔄 Data Flow and Relationships

### Querying Down the Hierarchy

To display a book in your collection, traverse from Item to Work:

```python

# Get all books in user's collection with full details
items = (
    db.session.query(Item)
    .join(Manifestation)
    .join(Expression)
    .join(Work)
    .filter(Item.owner_id == current_user.id)
    .all()
)

for item in items:
    # Access the full hierarchy
    title = item.manifestation.expression.work.title
    authors = item.manifestation.expression.work.meta.get("authors", [])
    isbn = item.manifestation.isbn13
    language = item.manifestation.expression.language
    condition = item.condition
```

### Creating New Entries: Work Deduplication

When adding a book, **always check if the Work already exists** to avoid duplicates:

```python
def add_book(isbn: str, metadata: dict) -> Item:
    """Add a book to collection, respecting FRBR hierarchy."""

    # 1. Check if Manifestation exists (by ISBN)
    manifestation = Manifestation.query.filter_by(isbn13=isbn).first()

    if not manifestation:
        # 2. Check if Work exists (by title)
        title = metadata["title"]
        authors = metadata["authors"]

        work = Work.query.filter_by(title=title).first()
        if not work:
            # 3. Create new Work
            work = Work(
                title=title,
                meta={"authors": authors}
            )
            db.session.add(work)
            db.session.flush()

        # 4. Create Expression for this language
        expression = Expression(
            work_id=work.id,
            content_type="text",
            language=metadata.get("language", "en")
        )
        db.session.add(expression)
        db.session.flush()

        # 5. Create Manifestation for this edition
        manifestation = Manifestation(
            expression_id=expression.id,
            isbn13=isbn,
            publisher=metadata.get("publisher"),
            publication_date=metadata.get("publication_date"),
            meta=metadata.get("extra_info", {})
        )
        db.session.add(manifestation)
        db.session.flush()

    # 6. Create Item (user's copy)
    item = Item(
        manifestation_id=manifestation.id,
        owner_id=current_user.id,
        status="available"
    )
    db.session.add(item)
    db.session.commit()

    return item
```

## 🧭 Faceted Navigation & Cross-FRBR Filtering

iqoqo provides multi-dimensional faceted search and aggregated statistics via `DataManager.get_faceted_stats`:

- **Cross-FRBR Filtering**: Queries cross FRBR boundaries using optimized SQL subqueries. Filters applied at the Manifestation level (e.g., format, publisher) or Item level (e.g., status, condition) filter aggregate counts across the Work and Expression tiers without cross-join inflation.
- **FRBR-Level Count Distinctions**: Facet aggregations accurately distinguish between overall catalog counts, total Work items, unique Manifestations, and user-owned physical Items.
- **Multi-Select Facet Logic**: Facets enforce `AND` logic across distinct facet fields (e.g., `content_type=text AND status=available`) and `OR` logic within multiple selections of the same facet field (e.g., `format=Hardcover OR format=Paperback`).
- **Ownership Facet Navigation**: Dedicated "Ownership" facet enables filtering entities by `owned` vs `not_owned` status across the FRBR hierarchy:
  - _Item tier_: Direct physical ownership by user ID (`Item.owner_id == user_id`).
  - _Manifestation tier_: Whether user owns at least one physical item copy of that manifestation.
  - _Expression tier_: Whether user owns an item realizing that expression.
  - _Work tier_: Whether user owns any item under any expression of that work. Inverse `not_owned` selects items where the user has zero physical holdings in that subtree.
- **Publisher Metadata Extraction**: Publisher facets extract publisher strings across both relational fields and JSON metadata blobs using SQL `func.coalesce(Manifestation.publisher, Manifestation.meta['publisher'].as_string())` `# pylint: disable=not-callable` to ensure full coverage.
- **Public Facet Endpoint**: Statistics and facet counts are exposed via `/api/stats/facets` protected by `@optional_auth`, allowing public visitors to filter public collection views.

## 📊 Dashboard Query Scoping & Metric Aggregations

To support clear differentiation between personal libraries and the collective repository, dashboard endpoints support query scoping:

- **`scope=personal` (default)**: Restricts summary counts (`/api/stats`), reading velocity (`/api/profile/insights/velocity`), and media distribution (`/api/profile/insights/distribution`) to entities associated with the authenticated user's physical items or `UserWorkIntent` wishlist entries.
- **`scope=global`**: Computes system-wide catalog aggregates across all public/registered items and manifestations, useful for exploring the complete institutional collection.

## 💬 In-App Feedback & User Ticket Architecture

iqoqo includes a native in-app feedback and bug tracking mechanism (`/api/feedback` and `/feedback` UI):

- **Feedback Ingestion**: Authenticated users can submit bug reports, feature requests, or general feedback with optional screenshot attachments (`multipart/form-data` stored securely under `/static/gallery/`).
- **Role-Based Access Control (RBAC)**:
  - `tickets:creator`: Granted to standard `user` role to submit tickets and manage/close their own submissions.
  - `tickets:admin`: Granted to `admin` role to review all user submissions, update lifecycle statuses (`new`, `in_progress`, `resolved`, `closed`), and post custodian resolution notes.

## 🛠️ Implementation Guidelines

### DO: Respect the Hierarchy

✅ **Correct**: Query through relationships

```python
# Get title from Work through the hierarchy
title = item.manifestation.expression.work.title
```

❌ **Incorrect**: Store denormalized data

```python
# DON'T duplicate title in Item or Manifestation
item.title = "The Hobbit"  # Wrong!
```

### DO: Check for Existing Works

✅ **Correct**: Deduplicate by title

```python
work = Work.query.filter_by(title=title).first()
if not work:
    work = Work(title=title, meta={"authors": authors})
```

❌ **Incorrect**: Create duplicate Works

```python
# DON'T create a new Work for every book
work = Work(title=title, meta={"authors": authors})  # Might duplicate!
```

### DO: Use Proper Foreign Keys

✅ **Correct**: Link through IDs

```python
expression = Expression(work_id=work.id, ...)
manifestation = Manifestation(expression_id=expression.id, ...)
item = Item(manifestation_id=manifestation.id, ...)
```

### DO: Store Data at the Right Level

- **Work level**: Title, authors, subject matter, original language
- **Expression level**: Specific language, content type (text/audio/video)
- **Manifestation level**: ISBN, publisher, publication date, page count, cover images
- **Item level**: Ownership, condition, personal notes, shelf location

## 🧪 Testing FRBR Implementation

Every feature that touches the data model must have tests that verify FRBR compliance:

```python
def test_frbr_hierarchy():
    """Verify proper FRBR hierarchy is maintained."""
    # Create hierarchy
    work = Work(title="Test Book", meta={"authors": ["Test Author"]})
    db.session.add(work)
    db.session.flush()

    expression = Expression(work_id=work.id, content_type="text", language="en")
    db.session.add(expression)
    db.session.flush()

    manifestation = Manifestation(expression_id=expression.id, isbn13="9781234567890")
    db.session.add(manifestation)
    db.session.flush()

    item = Item(manifestation_id=manifestation.id, owner_id="user123")
    db.session.add(item)
    db.session.commit()

    # Verify relationships
    assert item.manifestation.expression.work.title == "Test Book"
    assert item.manifestation.expression.work.meta["authors"] == ["Test Author"]
```

See [tests/test_web.py](../tests/test_web.py) for comprehensive FRBR hierarchy tests.

## 🔍 ISBN Lookup (`app/utils/isbn.py`)

External metadata is fetched via `app/utils/isbn.py`, which is the single place
responsible for all outbound HTTP calls to book metadata providers.

### Lookup pipeline

1. **Canonicalize** — `canonicalize_isbn(raw)` validates and normalises any
   ISBN-10 or ISBN-13 input (hyphens, spaces, mixed case) into a standard
   13-digit string. Returns `None` for invalid input.
2. **Google Books API** — queried first; fast, high availability, no API key
   required for low-volume usage.
3. **Open Library Books API** — fallback; broader language coverage and fully
   open data. Same retry/timeout policy.

### Retry and timeout policy

Both upstream calls use a shared `requests.Session` with:

- **Connect timeout**: 15 s (TCP + TLS handshake)
- **Read timeout**: 45 s (full response body)
- **Retries**: 3 attempts, 1.5× exponential back-off, on HTTP 429/500/502/503/504

This handles cold-start DNS latency and transient upstream errors without
blocking the caller for too long.

### Response shape

Both adapters normalise their response to:

```python
{"Title": str, "Authors": list[str]}
```

The route in `app/api/routes.py` stores this in the FRBR hierarchy
(`Work.title`, `Work.meta["authors"]`, `Manifestation.meta`) so subsequent
lookups of the same ISBN are served from the local database.

### Cover Generation Pipeline

- **Real-time Lookup:** Fast APIs (OpenLibrary, Google Books) run synchronously during item creation to provide immediate UI feedback.
- **Asynchronous Generation:** If fast lookup fails, item metadata is marked `cover_status: "pending"` and a background thread orchestrates LLM generation (Local SD -> Gemini -> OpenAI).
- **Optimization:** All generated covers are converted to `JPEG` at 85% quality to prevent storage bloat, while maintaining their 1024x1024 resolution.
- **Maintenance:** A daily cron job (`scripts/archive_orphans.py`) sweeps `app/static/covers` and archives physical files that no longer have matching DB records.

## Authentication and Authorization (v0.1.0)

Iqoqo uses a hybrid authentication approach suitable for distributed deployments:

1. **SSO / Local Identity**: Users can register via standard email/password or use Google SSO (via Authlib).
2. **JWT & BFF Pattern**: The Python backend generates a stateless JWT and redirects the browser to the Next.js Backend-For-Frontend (BFF) route (`/api/auth-exchange`). That route handler catches the token and stores it securely in an `HttpOnly` cookie.
3. **Next.js Auth Guard (current behavior)**: A small helper used by protected routes (for example, `/collection`, `/profile`) checks for the presence of the auth cookie set by the BFF route before rendering pages. JWT signature and expiry verification are enforced on the Python backend; the Next.js layer currently treats the cookie as an opaque session token. A future iteration may introduce Edge middleware using `jose` for full client-side verification.
4. **RBAC**: The database implements an RBAC matrix (`Role`, `Permission`, `user_roles`). Backend API endpoints are protected using `@require_auth` and `@require_permission` decorators.

   > **Frontend RBAC and UI State:**
   > To ensure the user interface accurately reflects backend authorization rules (as tested in `test_api.py`), the frontend utilizes the `useProfile` hook which exposes `profile.permissions`. Components like `ItemActions` dynamically mount buttons based on the current user's permissions.
   >
   > **Note:** UI hiding is purely cosmetic; all associated API routes enforce strict validation on the backend.

5. **Data Privacy**: Granular GDPR consents (Telemetry, Federation) are tracked per user in the `user_consents` table with explicit opt-in mechanics.
6. **FRBR Boundary Enforcement (`@require_physical_item`)**: API endpoints operating on physical item features (e.g., updating physical condition or shelf location) use the `@require_physical_item` decorator. If invoked on a virtual item (negative ID / `UserWorkIntent`), the decorator intercepts the call before execution and returns a standardized `400 Bad Request` JSON error response:

   ```json
   {
     "error": "This action requires a physical item. Modify the wishlist item to convert it to a physical item first.",
     "code": 400
   }
   ```

7. **Hybrid Public/Authenticated Access (`@optional_auth`)**: Public catalog endpoints (such as `/api/manifestations` and `/api/stats/facets`) use `@optional_auth`. Unauthenticated visitors can browse global catalog stats and manifestations, while authenticated requests automatically resolve `current_user` to return personalized ownership flags and wishlist statuses.

## ⚙️ Operations & Maintenance

### Backup & Restore

iqoqo uses a cloud-first backup strategy via `scripts/cloud_backup.sh`, triggered by system cron.

**Backup:**

The cloud backup script performs a full disaster-recovery dump:

1. `pg_dumpall` of the PostgreSQL database (raw SQL)
2. Archives of asset directories: `covers/`, `gallery/`, `uploads/raw_covers/`
3. Compression into a single `.tar.gz`
4. Sync to an rclone cloud remote (S3, Google Drive, etc.)

- **Manual run:** `make backup-run remote=<rclone_remote_name>`
- **Install cron:** `make backup-install remote=<name>` — schedules daily at 03:00
- **Health check:** `make backup-check remote=<name>` — verifies cron, rclone, disk, freshness

**Ad-hoc JSON export (data portability):**
Run `make db-export` to export the database as JSON to `exports/backup.json`. This is useful for instance-to-instance data migration, not disaster recovery.

#### Background Scheduler

The in-app APScheduler (`app/core/scheduler.py`) runs a cover cleanup watchdog every 5 minutes to reset stuck cover tasks. Enable via `SCHEDULER_AUTOSTART=true`.

> **Flask Application Context**: Scheduled background jobs run outside HTTP request lifecycles. Functions executed by APScheduler (such as `run_scheduled_cover_cleanup()`) must explicitly create an application context using `with scheduler.app.app_context():` to safely access database sessions and application configuration without raising a `RuntimeError`.

### Format Normalization

External APIs (such as OpenLibrary, Google Books, or Discogs) return raw format strings that vary wildly (e.g., `"Mass Market Paperback"`, `"hardcover"`, `"Vinyl LP"`). iqoqo normalizes these into canonical `MediaFormat` identifiers:

- **Pipeline**: `app/core/format_normalizer.py` converts external string values into canonical `MediaFormat` enum values using `shared/format_mappings.yaml` as the git-tracked Single Source of Truth (SSoT).
- **Unknown Format Placeholders**: If an external format cannot be mapped, fallback placeholders (`unknown_video`, `unknown_audio`, `unknown_text`) are assigned to preserve dataset validity.
- **CLI Maintenance**: The `make fix-physical-kinds` CLI command audits existing physical items, flags non-canonical format entries, and interactively or automatically applies normalization mappings directly in the database (`--audit`, `--dry-run`, `--apply`).

**Restore:**
Run `python scripts/restore_covers.py <path_to_zip>` to restore cover images and update their metadata in the database.

- This script is "safe" — it updates existing records matching by ISBN/ID but does not wipe the database.
- **HINT:** On production run `docker compose exec web python scripts/restore_covers.py <path_to_zip>`

### Archiving Orphaned Covers

When books are deleted, their cover images remain on disk. To clean up:

```bash
python scripts/archive_orphans.py
```

This moves unused images to an archive folder.

- **Configuration:** Set `COVERS_ARCHIVE_DIR` env var to customize the archive location (default: `app/static/archive/covers`).

### Video / Film Metadata (FRBRoo Event-Based)

For video media (Blu-Rays, DVDs, VHS) the FRBR hierarchy leverages the existing Audio contributor models for Creation and Performance, but adds Publication events:

```text
Contributor  ←── ManifestationContribution  ←── Manifestation    (Publication Event)
```

Valid `ManifestationContribution.role` values: `studio`, `distributor`, `producer`, `network`.
Video-specific keys in `Manifestation.meta`: `resolution`, `aspect_ratio`, `video_format`, `audio_formats`, `run_time_minutes`.

### Board Game Metadata (FRBRoo Container Work)

Board games are modeled as an F16 Container Work (the Box) which aggregates distinct components:

```text
Work (The Box)  ←── ContainerAggregation  ──→ Work (Rulebook / Scenarios)
Work (The Box)  ←── ContainerAggregation  ──→ Item (Game Board / Pieces / Meeples)
```

Game-specific keys in `Manifestation.meta`: `min_players`, `max_players`, `playtime_minutes`, `min_age`, `game_mechanics`, `designer`.

### 5. F16 Container Work (Board Games)

**Database**: `catalog.container_aggregations` table (linking `works` and `items`)

For board games, iqoqo extends the basic FRBR hierarchy using the **FRBRoo F16 Container Work** pattern. A board game box is a container that holds multiple disparate items and works.

**Examples**:

- The "Catan" base game box.
- Inside the box: The Rulebook (F1 Work), The Game Board (F5 Item), 15 Road pieces (F5 Items).

**Attributes (`container_aggregations`)**:

- `container_work_id` - Foreign key to the main game's Work.
- `aggregated_type` - Type of component ('work' or 'item').
- `aggregated_work_id` / `aggregated_item_id` - Link to the specific rulebook or physical piece.
- `component_name` - "Red Meeples", "Main Board", etc.
- `quantity` - Number of identical pieces.

**Key Principle**: The main board game is an F16 Container. Its mechanics, min/max players, and playtime are stored in the Manifestation's `meta` JSON. The physical pieces and rulebooks are aggregated into this container, allowing users to track missing components.

```python
# Board Game as a Container
game_work = Work(title="Catan", meta={"categories": ["Board Game"]})

# Aggregating a rulebook
rulebook_work = Work(title="Catan Almanac")
aggregation1 = ContainerAggregation(
    container_work_id=game_work.id,
    aggregated_type='work',
    aggregated_work_id=rulebook_work.id,
    component_name="Almanac",
    quantity=1
)
```

## 🌐 Frontend Architecture (Phase 2)

iqoqo uses a **decoupled** architecture where the Flask application serves only JSON
via `app/api/` and the React/Next.js frontend is a fully independent application living
in `frontend/`.

### Technology Stack

| Layer        | Technology                             | Notes                          |
| ------------ | -------------------------------------- | ------------------------------ |
| Framework    | Next.js 16 (App Router)                | SSR + RSC hybrid               |
| Language     | TypeScript 5                           | Strict mode                    |
| Styling      | Tailwind CSS v4                        | CSS-based `@theme` config      |
| Server state | TanStack React Query v5                | Caching, retries               |
| HTTP client  | Axios                                  | Wraps `NEXT_PUBLIC_API_URL`    |
| Toasts       | Sonner                                 | Rich toast notifications       |
| Scanner      | ZXing (@zxing/browser, @zxing/library) | ISBN barcode via device camera |
| Fonts        | Merriweather (serif) + Inter (sans)    | Google Fonts                   |

### Design System – "Modern Athenaeum"

All design tokens live in `frontend/app/globals.css` as CSS custom properties mapped
into Tailwind v4 via `@theme inline`.

| Token                | Value                           | Usage                  |
| -------------------- | ------------------------------- | ---------------------- |
| `--color-primary`    | Deep Indigo `hsl(210 29% 24%)`  | Nav, headings, CTA     |
| `--color-accent`     | Library Clay `hsl(24 100% 41%)` | Accent, badges         |
| `--color-background` | Warm Paper `hsl(43 50% 98%)`    | Page background        |
| `--font-serif`       | Merriweather                    | Display text, headings |
| `--font-sans`        | Inter                           | Body, labels           |

### Directory Structure

```text
frontend/
├── app/                   # Next.js App Router
│   ├── globals.css        # Design system tokens (Tailwind v4 @theme)
│   ├── layout.tsx         # Root layout + Providers
│   ├── page.tsx           # Dashboard (/)
│   ├── collection/
│   │   └── page.tsx       # Collection browser
│   ├── item/[id]/
│   │   └── page.tsx       # Item detail
│   └── scan/
│       └── page.tsx       # Barcode scanner
├── components/
│   ├── dashboard/         # Navbar, StatsCards, CurrentContext, FreshArrivals
│   ├── collection/        # ItemCard, FilterBar, SidebarFilters, CollectionGrid
│   ├── item/              # HeroBanner, ItemHeader, ItemSidebar, ItemTabs
│   └── scanner/           # TopBar, Viewfinder, BottomSheet, SuccessCard
├── lib/
│   ├── utils.ts           # cn() class merging helper
│   └── api/
│       ├── client.ts      # Axios instance + apiFetch() helper
│       └── hooks.ts       # React Query hooks for all endpoints
└── types/
    └── frbr.ts            # TypeScript types mirroring the FRBR data model
```

### API Integration Pattern

The frontend communicates with Flask via a standardised JSON envelope:

```jsonc
// Every endpoint returns this shape
{
  "success": true,
  "data": {
    /* entity or list */
  },
  "error": null, // string when success=false
  "meta": {
    // present on paginated endpoints only
    "page": 1,
    "limit": 20,
    "total": 1562,
    "pages": 79,
  },
}
```

The `apiFetch<T>()` helper in `lib/api/client.ts` unwraps this envelope and throws
a typed error when `success` is `false`.

### Item Status Values

The `Item.status` column accepts exactly these values. The canonical Python
definition is `ITEM_STATUSES` in `app/db/core.py`; the TypeScript mirror is
`ItemStatus` in `frontend/types/frbr.ts`. The cross-subsystem contract is
enforced by `tests/test_ontology.py`.

| Status           | Meaning                            | Media |
| ---------------- | ---------------------------------- | ----- |
| `available`      | On your shelf, ready to use        | All   |
| `lent`           | Lent to a friend                   | All   |
| `lost`           | Cannot be located                  | All   |
| `wish_list`      | Want to acquire (owned or not)     | All   |
| `ordered`        | Purchased, awaiting delivery       | All   |
| `damaged`        | Physically damaged copy            | All   |
| `reading`        | Currently being read               | Text  |
| `read`           | Finished reading                   | Text  |
| `unread`         | Never opened                       | Text  |
| `listening`      | Currently playing / listening to   | Audio |
| `listened`       | Finished listening                 | Audio |
| `want_to_listen` | On audio wishlist (do not own yet) | Audio |

### Database Schema Layout

Tables are split across PostgreSQL schemas:

| Schema      | Tables                                                                    |
| ----------- | ------------------------------------------------------------------------- |
| `auth`      | `users`, `roles`, `permissions`, `user_roles`, `role_permissions`,        |
|             | `token_blocklist`, `user_consents`                                        |
| `catalog`   | `works`, `expressions`, `manifestations`, `contributors`,                 |
|             | `work_contributions`, `expression_contributions`,                         |
|             | `manifestation_contributions`, `work_parts`,                              |
|             | `work_expansion_links`, `boardgame_mechanics`,                            |
|             | `container_aggregations`, `instance_settings`                             |
| `inventory` | `items`, `llm_telemetry`, `shared_collections`, `shared_collection_items` |
| `social`    | `feedback_items`, `feedback_comments`, `escalation_requests`              |
| `public`    | `alembic_version`                                                         |

### Model File Structure

Model classes are split into domain-focused modules under `app/db/`:

| File          | Contents                                                                                                  |
| ------------- | --------------------------------------------------------------------------------------------------------- |
| `auth.py`     | `User`, `Role`, `Permission`, `TokenBlocklist`, `ConsentRecord`                                           |
| `core.py`     | `Work`, `WorkExpansionLink`, `BoardgameMechanic`, `Expression`, `Manifestation`, `Item`, `ITEM_STATUSES`  |
| `audio.py`    | `Contributor`, `WorkContribution`, `ExpressionContribution`, `WorkPart`,                                  |
|               | `MANIFESTATION_AUDIO_META_KEYS`                                                                           |
| `video.py`    | `ManifestationContribution`, `MANIFESTATION_VIDEO_META_KEYS`                                              |
| `games.py`    | `ContainerAggregation`, `MANIFESTATION_GAME_META_KEYS`                                                    |
| `social.py`   | `SharedCollection`, `FeedbackItem`, `FeedbackComment`, `EscalationRequest`                                |
| `history.py`  | `ItemCustodyEvent` (append-only physical possession tracking),                                            |
|               | `EntityAuditLog` (Work/Expression/Manifestation curation logs)                                            |
| `settings.py` | `LLMTelemetry`, `InstanceSettings`                                                                        |
| `models.py`   | Re-export shim — `from app.db.models import Work` continues to work                                       |

### Item Custody & Entity Audit Logs

To maintain strict ontological separation between physical item possession and conceptual metadata changes, iqoqo implements CIDOC CRM-aligned audit tables:

- **`ItemCustodyEvent`** (`inventory` schema): Append-only audit log tracking physical Item tier transfers, location changes, lending events, and condition alterations.
- **`EntityAuditLog`** (`catalog` schema): Tracks editorial curation, metadata updates, deduplication merges, and schema migrations at the Work, Expression, and Manifestation tiers.

### Board Game Expansions (F15 Complex Work Decomposition)

Starting in **v0.7.16**, board game expansions are modeled as distinct `F1_Work` entities linked to their base game via `work_expansion_links`:

```text
Base Game (Work)  ←── WorkExpansionLink (is_expansion_of) ──  Expansion (Work)
```

- **Ontology Alignment**: Reifies `iqoqo:is_expansion_of` and its inverse `iqoqo:has_expansion` in `docs/ontology/iqoqo.ttl`.
- **SHACL Integrity Guard**: Defined in `docs/ontology/iqoqo-shapes.ttl` and enforced at runtime via `validate_work_not_expansion_aggregated()`. A Work linked as an expansion cannot be aggregated as a component into an F16 Container Work box (`container_aggregations`).

### Board Game Mechanics Taxonomy

Board game mechanics use a canonical controlled vocabulary backed by `boardgame_mechanics` in the `catalog` schema:

- **Data Source**: Seedable canonical JSON located at `data/bgg_mechanics.json`.
- **API Endpoint**: `GET /api/taxonomies/boardgame-mechanics` returns the structured list of mechanics.
- **Frontend Component**: Rendered uniformly via the `MechanicBadge` component.

### Audio / Music Metadata (FRBRoo Event-Based)

For audio media (CDs, Vinyls, Audiobooks) the FRBR hierarchy is extended

with FRBRoo event-based contributor tables in the `catalog` schema:

```text
Contributor  ←── WorkContribution  ←── Work          (Composition Event)
Contributor  ←── ExpressionContribution ←── Expression  (Performance Event)
Work  ←── WorkPart ←── Work                           (F15 Complex Work — box sets)
```

Valid `WorkContribution.role` values: `composer`, `lyricist`, `author`, `playwright`, `arranger`

Valid `ExpressionContribution.role` values: `performer`, `conductor`, `narrator`, `band`, `director`, `ensemble`

Audio-specific keys that **may** be stored in `Manifestation.meta`:

| Key               | Type    | Description                                                   |
| ----------------- | ------- | ------------------------------------------------------------- |
| `catalog_number`  | string  | Record-label catalog number (e.g. `"ECM 1064"`)               |
| `pressing_number` | string  | Specific pressing identifier                                  |
| `matrix_number`   | string  | Vinyl run-out groove / lacquer ID                             |
| `label`           | string  | Record label name (e.g. `"Blue Note"`)                        |
| `format`          | string  | Physical format: `LP`, `45`, `EP`, `CD`, `CD-EP`, …           |
| `disc_count`      | integer | Number of discs in a multi-disc release                       |
| `track_list`      | list    | `[{"position": "A1", "title": "…", "duration_seconds": 210}]` |

### Local Development

```bash
# Start everything in one command:
./run_dev.sh

# Or separately:
docker compose up -d db                 # PostgreSQL
flask --app run run                      # API on :5000
cd frontend && npm run dev              # React on :3000
```

See [docs/INSTALL.md](INSTALL.md) for full setup instructions.

## 📖 Further Reading

- **FRBRoo Specification**: [https://www.ifla.org/publications/node/11240](https://www.ifla.org/publications/node/11240)
- **FRBR Family**: [https://www.ifla.org/frbr](https://www.ifla.org/frbr)
- **iqoqo Ontology**: [docs/ontology/iqoqo.ttl](ontology/iqoqo.ttl)

## 🤝 Questions?

If you're unsure about where data should live in the FRBR hierarchy:

1. Ask: "Is this about the **concept** (Work), the **version** (Expression), the **edition** (Manifestation), or **my copy** (Item)?"
2. Check the [models.py](../app/db/models.py) documentation
3. Look at existing tests in [tests/test_web.py](../tests/test_web.py)
4. Open an issue for discussion

Remember: **When in doubt, follow the hierarchy!**

## 👥 Social & Privacy Architecture (v0.7.0+)

Phase 1 of v0.7.0 introduces opt-in social features while maintaining strict user privacy.

### 1. Opt-in Exposure

- **`User.visibility`**: Reuses the existing `visibility` field. Only users with `visibility="public"` are discoverable via `/u/[username]`.
- **`User.public_username`**: A unique, customizable handle used for public URLs.
- **`User.bio`**: Optional public text for personalized profiles.

### 2. Item-Level Privacy

- **`Item.is_hidden`**: A granular toggle. Even if a profile is public, specific items can be hidden from the public grid.
- **BOLA Protection**: All visibility toggles verify `owner_id`. Unauthorized access attempts return `404 Not Found` rather than `403 Forbidden` to prevent account enumeration.

### 3. Dynamic Shared Collections

- **`SharedCollection`**: Stores a secure `share_token` linked to a set of JSONB filters (e.g., `{"status": "wish_list"}`).
- **Access**: Shared collections are accessible to anyone with the token, bypassing the general profile visibility if the specific collection was shared.

### 4. Smart Inventory Discovery

- **"Check if I have it"**: A visitor-facing tool that searches the joined FRBR chain (`Item` → `Manifestation` → `Expression` → `Work`).
- **Logic**: If an exact match is found in the owner's collection, it returns the Item details. If not owned but exists in the global catalog, it returns the Manifestation details to indicate the item is known to iqoqo.

### 5. Shared Collection UI Patterns

- **Token-Based Access**: Shared collections operate via unique `share_token` URLs, granting read-only access to specific filtered items without exposing account details.
- **Simplified Navigation**: When viewing a shared collection, the frontend renders a simplified top navbar without personal collection navigation or administrative controls.
- **Hidden Action Buttons**: Interactive item controls (edit, delete, status toggle, tag modification) are hidden for unauthenticated viewers of shared links.

### 6. Feedback & Escalation Subsystem (v0.7.15 - v0.7.16)

- **Dedicated Social Schema**: Feedback models (`FeedbackItem`, `FeedbackComment`) reside in PostgreSQL `social` schema with relational normalization for thread comments.
- **FRBR Target Entity Linkage**: `FeedbackItem.target_entity` (JSONB) links user bug reports directly to specific FRBR entities (`{"entity_type": "manifestation", "entity_id": 123}`), bridging user feedback with custodian escalation queues.
- **Cloud Attachment Sync**: Feedback attachments support asynchronous upload via `rclone copyto --` using the `RCLONE_FEEDBACK_REMOTE` environment variable with seamless local storage fallback.

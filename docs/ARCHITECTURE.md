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
   13-digit string.  Returns `None` for invalid input.
2. **Google Books API** — queried first; fast, high availability, no API key
   required for low-volume usage.
3. **Open Library Books API** — fallback; broader language coverage and fully
   open data.  Same retry/timeout policy.

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

## ⚙️ Operations & Maintenance

### Backup & Restore

iqoqo includes scripts to manage data portability and disaster recovery.

**Backup:**
Run `python scripts/backup.py` to create a ZIP archive containing the database dump (`metadata.json`) and the `covers/` directory.

- **Configuration:** Set `BACKUP_DIR` env var to customize the output location (default: `exports/`).

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
  "data": { /* entity or list */ },
  "error": null,           // string when success=false
  "meta": {               // present on paginated endpoints only
    "page": 1,
    "limit": 20,
    "total": 1562,
    "pages": 79
  }
}
```

The `apiFetch<T>()` helper in `lib/api/client.ts` unwraps this envelope and throws
a typed error when `success` is `false`.

### Item Status Values

The `Item.status` column accepts exactly these values.  The canonical Python
definition is `ITEM_STATUSES` in `app/db/models.py`; the TypeScript mirror is
`ItemStatus` in `frontend/types/frbr.ts`.  The cross-subsystem contract is
enforced by `tests/test_ontology.py`.

| Status      | Meaning              |
| ----------- | -------------------- |
| `available` | On your shelf        |
| `lent`      | Lent to a friend     |
| `lost`      | Cannot be located    |
| `wish_list` | Want to acquire      |
| `reading`   | Currently being read |
| `read`      | Finished reading     |

### Local Development

```bash
# Start everything in one command:
./run_dev.sh

# Or separately:
docker-compose up -d db                 # PostgreSQL
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

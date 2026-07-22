# Installation Guide

This document provides comprehensive instructions for setting up iqoqo for development and production use.

## Quick Start (Docker)

For the fastest setup, use Docker Compose:

```bash
# 1. Clone and navigate to the repository
git clone https://github.com/sebastiankruk/iqoqo.git
cd iqoqo

# (Optional) Login to GitHub Container Registry for pre-built images
# If pull fails, the script will offer to login via GitHub CLI (gh)
gh auth token | docker login ghcr.io -u your-username --password-stdin

# 2. Create and configure environment file
cp .env.example .env
# Edit .env: Set DATABASE_URL, configure ports, set strong passwords, and CORS values if needed

# 3. Build and start services (migrations run automatically on first start)
./run.sh prod

# (Optional) To enable local AI generation (requires powerful hardware):
# docker compose --profile local-ai up -d

# 4. (Optional) Load sample data
docker compose exec web python scripts/init_db.py --seed-file data/seed_example.json

# 5. Initialize the admin user (uses ADMIN_EMAIL and ADMIN_PASSWORD from .env)
docker compose exec web python scripts/init_auth.py

# 6. Access the application
# http://localhost:5000 (or your configured WEB_PORT)
```

For detailed configuration and development setup, continue reading below.

## Prerequisites

### Required Software

- **Python 3.14+** - [Download](https://www.python.org/downloads/)
- **Node.js 20+** and **npm** - [Download](https://nodejs.org/)
- **PostgreSQL 16-alpine+** - Can be run via Docker (recommended) or installed locally
- **Docker & Docker Compose** - For containerized deployment
- **Git** - For version control

## Docker Installation

Docker is required to run the PostgreSQL database in a container.

- **macOS**: You can install [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/), but be aware of its licensing terms. For a free and open-source alternative, we recommend [Colima](https://github.com/abiosoft/colima). You can install it using [Homebrew](https://brew.sh/):

  ```bash

  brew install colima docker docker-compose
  colima start
  ```

- **Ubuntu**: Follow the instructions to install [Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/) and the [Docker Compose plugin](https://docs.docker.com/compose/install/linux/).

After installation, make sure the Docker daemon is running.

## Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/your-username/iqoqo.git
   cd iqoqo
   ```

2. **Create and activate a virtual environment:**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Python dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

   This installs both runtime dependencies and development tools (black, ruff, isort, mypy, pytest).

4. **Install JavaScript/CSS quality tools:**

   ```bash
   npm install
   ```

   This installs ESLint, Prettier, stylelint, and markdownlint for code quality checks.

5. **Set up environment variables:**

   Create a `.env` file by copying the example file:

   ```bash
   cp .env.example .env
   ```

   **Important:** Edit the `.env` file to configure your deployment:
   - **For Docker deployment:** Set `DATABASE_URL` to use `db` as the hostname:

     ```text
     DATABASE_URL="postgresql://iqoqo:your_password@db:5432/iqoqo"
     ```

   - **For local development:** Set `DATABASE_URL` to use `localhost`:

     ```text
     DATABASE_URL="postgresql://iqoqo:your_password@localhost:5432/iqoqo"
     ```

   - **Port configuration:** If you have other services running (like other Flask apps or Home Assistant), change the ports to avoid conflicts:

     ```text
     WEB_PORT=8000    # External port for web access (default: 5000)
     DB_PORT=5433     # External port for database access (default: 5432)
     ```

   - **Security:** Generate strong credentials for production:

     ```bash
     # Generate a strong secret key
     python -c "import secrets; print(secrets.token_hex(32))"

     # Use a strong database password
     # Update POSTGRES_PASSWORD and DATABASE_URL with the same password
     ```

   - **CORS (for separate frontend origin):** Keep CORS disabled unless needed. If your frontend is served from a different origin, configure explicit origins:

     ```text
     CORS_ENABLED=true
     CORS_ORIGINS="https://app.example.com,https://admin.example.com"
     CORS_SUPPORTS_CREDENTIALS=false
     ```

   - **Barcode Resolution Pipeline:** If you plan to use barcode scanning for physical media (DVDs, Games, Puzzles), you should register for API keys at:
     - [upcdatabase.org](https://upcdatabase.org/) (Tier 1a Open Data)
     - [upcitemdb.com](https://upcitemdb.com/) (Tier 1b high-quality data)
     - [Allegro Developer](https://apps.developer.allegro.pl/) (Tier 2 retail resolve & covers)
       > **Allegro Setup Note:** The Allegro Developer portal requires you to select _at least one_ permission, such as **`allegro:api:sale:offers:read`**. Set the **Redirect URI** to `http://localhost`.
       > **⚠️ IMPORTANT:** Allegro requires "User Context" for search. After setting your `CLIENT_ID` and `CLIENT_SECRET` in `.env`, you **MUST** run the authentication script once:
       >
       > ```bash
       > python scripts/allegro_auth.py
       > ```
       >
       > Follow the on-screen instructions to authorize the app. This creates a `.allegro_token.json` file used for future searches.

     Add these to your `.env` as `UPC_DATABASE_ORG_KEY`, `UPC_ITEM_DB_KEY`, `ALLEGRO_CLIENT_ID`, and `ALLEGRO_CLIENT_SECRET`.

     > **Multi-Environment Deployments:** If you run multiple iqoqo instances (prod, preview, dev) with separate Allegro app registrations, also set `ALLEGRO_APP_NAME` to the registered application name (e.g. `iqoqo_cc`, `iqoqo_pre`, `iqoqo_dev`). Allegro validates the `User-Agent` header against this name.

   - **Local AI Generation:** If you plan to use a local LLM for cover generation, see LOCAL_AI_SETUP.md for detailed instructions on setting up Stable Diffusion.

     Set `CORS_SUPPORTS_CREDENTIALS=true` only when your auth flow requires credentialed cross-origin requests.

   > **Note for VS Code users:** To have the environment variables from the `.env` file automatically loaded in the integrated terminal, you need to enable the `python.terminal.useEnvFile` setting. You can do this by opening your VS Code settings (JSON) and adding `"python.terminal.useEnvFile": true`.

### Format Normalization Configuration (`shared/format_mappings.yaml`)

iqoqo uses `shared/format_mappings.yaml` as the git-tracked Single Source of Truth (SSoT) for mapping external API format strings (e.g. `"Mass Market Paperback"`, `"hardcover"`, `"Vinyl LP"`) to canonical `MediaFormat` identifiers:

```yaml
# shared/format_mappings.yaml mapping structure
format_normalizations:
  # Exact string match mappings
  video: dvd
  audio: cd
  hardcover: hardcover
  paperback: paperback

  # Scoped fallback mappings for NULL values
  null:
    movie: dvd
    music: cd
    text: book
```

Run `make fix-physical-kinds` (`--audit`, `--interactive`, `--dry-run`, `--apply`) to inspect and normalize stored physical item formats.

## Environment Variable Hierarchy

iqoqo uses a layered approach to configuration to support seamless switching between local development, tunneled development, and production Docker environments.

### Backend (Flask & Celery)

| File | Loaded By | Purpose |

| :------------- | :-------- | :----------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`.env`** | Global | **Primary source of truth.** Contains shared defaults for DB names, API keys, and production service names (e.g., `REDIS_URL=redis://redis`). |
| **`.env.dev`** | `run.sh` | **Local Overrides.** Only loaded during `./run.sh dev`. Use this to override container hostnames with `localhost` or change ports for local processes. |

**Inheritance Logic:**

1. The startup script loads `.env` first.
2. If in a specific mode (e.g., `preview`), it then loads `.env.preview`, which **overwrites** any values set in `.env`.
3. Note: Commenting out a variable in a mode-specific `.env` file does **not** unset it from the environment; it will simply fall back to the value defined in `.env`. To "disable" a variable, set it to an empty string (`VAR=`).

### Frontend (Next.js)

| File             | Loaded By | Purpose                                                                                                                                                  |
| :--------------- | :-------- | :------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`.env`**       | Next.js   | Shared defaults for the frontend.                                                                                                                        |
| **`.env.local`** | Next.js   | **Local Overrides.** Standard Next.js file for local machine settings. This file is git-ignored and should be used for secrets or machine-specific URLs. |

**Note:** Only variables prefixed with `NEXT_PUBLIC_` are accessible in the browser.

## Database Setup

This project uses PostgreSQL as its database. You have two options:

> **Migrations run automatically** — you do not need to run `flask db upgrade` manually
> in either the development or production workflows described below.
> See the [Database Migrations](#database-migrations) section for details.

### Option A: Local Development (Database Only in Docker)

Use this option if you want to run the Flask application on your host machine but use a containerized PostgreSQL database.

1. **Start the database service:**

   ```bash
   docker compose up -d db
   ```

   This starts only the PostgreSQL container. Make sure your `.env` file has:

   ```text
   DATABASE_URL="postgresql://iqoqo:password@localhost:5432/iqoqo"
   ```

2. **Start the application (migrations run automatically):**

   ```bash
   ./run.sh dev
   ```

   `run.sh dev` activates the virtual environment, runs `flask db upgrade` to apply any
   pending migrations, and then starts both the Flask API and Next.js dev server.

3. **Initialize with seed data (optional):**

   If you have a JSON export file from a previous iqoqo instance or want to import data:

   ```bash
   python scripts/init_db.py --seed-file path/to/data.json
   ```

   This will only import data if the database is empty.

4. **Initialize the admin account:**

   To log in, you must create the initial admin user using the credentials specified in your `.env` file (`ADMIN_EMAIL` and `ADMIN_PASSWORD`):

   ```bash
   PYTHONPATH=. .venv/bin/python scripts/init_auth.py
   ```

### Option B: Full Docker Deployment (Production)

Use this option to run both the Flask application and PostgreSQL database in containers. This is the recommended approach for production deployments.

1. **Configure environment variables:**

   Make sure your `.env` file is configured for Docker:

   ```text
   # Use 'db' as hostname for container-to-container communication
   DATABASE_URL="postgresql://iqoqo:your_password@db:5432/iqoqo"

   # Set external ports (change if you have other services running)
   WEB_PORT=8000    # or 5000 if available
   DB_PORT=5433     # or 5432 if available

   # Use production settings
   FLASK_ENV=production

   # Configure CORS explicitly when frontend and API use different origins
   CORS_ENABLED=true
   CORS_ORIGINS="https://app[.]example.com"
   CORS_SUPPORTS_CREDENTIALS=false
   ```

2. **Start Production Services:**

   Use the provided production command to build and launch the stack using Nginx:

   ```bash
   ./run.sh prod
   ```

   If you need to use `sudo` with Docker:

   ```bash
   sudo ./run.sh prod
   ```

3. **Initialize with seed data (optional):**

   ```bash
   docker compose exec web python scripts/init_db.py --seed-file data/seed_example.json
   ```

4. **Verify deployment:**

   ```bash
   # Check container status
   docker compose ps

   # View logs
   docker compose logs -f web

   # Test the application
   curl http://localhost:8000/api/stats
   ```

The application will be available at `http://localhost:8000` (via Nginx).

#### Docker Management Commands

```bash
# View logs
docker compose logs -f web    # Follow web application logs
docker compose logs -f db     # Follow database logs

# Restart services
docker compose restart web
docker compose restart db

# Stop all services
docker compose down

# Stop and remove volumes (⚠️ this deletes all database data!)
docker compose down -v

# Rebuild after code changes
docker compose build
docker compose up -d

# Execute commands in containers
docker compose exec web flask db upgrade
docker compose exec db psql -U iqoqo -d iqoqo

# View running containers and resource usage
docker compose ps
docker stats --no-stream
```

## Database Migrations

iqoqo uses [Alembic](https://alembic.sqlalchemy.org/) via [Flask-Migrate](https://flask-migrate.readthedocs.io/)
to manage database schema changes. Every structural change — new columns, renamed tables,
new indexes — is captured in a versioned migration file under `migrations/versions/`.

### When migrations run

| Workflow                             | How migrations run                                                                                              |
| ------------------------------------ | --------------------------------------------------------------------------------------------------------------- |
| **Local dev** (`./run.sh dev`)       | Automatically — `flask db upgrade` is called before Flask starts.                                               |
| **Docker dev** (`docker compose up`) | Automatically — the `web` container waits for the db healthcheck, then runs `flask db upgrade` before gunicorn. |
| **Docker prod** (`./run.sh prod`)    | Same as Docker dev — automatic on every container start.                                                        |

`flask db upgrade` is **idempotent**: running it when the schema is already current is
completely safe and takes only a fraction of a second. It is therefore safe to run on
every startup without any guard condition.

### Running migrations manually

If you need to run migrations outside the normal startup flow:

```bash
# Local development (venv must be active):
source .venv/bin/activate
flask db upgrade

# Inside a running Docker container:
docker compose exec web flask db upgrade
```

### Viewing migration history

```bash
# Show current revision applied to the database:
flask db current

# Show full migration history:
flask db history
```

### Adding a new migration (for contributors)

When you change a SQLAlchemy model in `app/db/models.py`, generate a new migration
file with:

```bash
# Autogenerate a migration from the model diff:
flask db migrate -m "short description of the change"

# Review the generated file in migrations/versions/, then apply it:
flask db upgrade
```

Always review the auto-generated file — Alembic cannot detect every change (e.g.
column renames, constraint name changes). Add manual SQL where necessary and include
a matching `downgrade()` function so the migration can be rolled back.

### Data Import/Export

iqoqo provides comprehensive data management capabilities through both CLI scripts and API endpoints.

#### Export Data Format

The iqoqo export format is a JSON file with the following structure:

```json
{
  "version": "1.0",
  "exported_at": "2026-01-29T10:30:00.000000",
  "works": [
    {
      "id": 1,
      "title": "The Hobbit",
      "meta": {
        "authors": ["J.R.R. Tolkien"],
        "categories": ["Fantasy", "Adventure"]
      }
    }
  ],
  "expressions": [
    {
      "id": 1,
      "work_id": 1,
      "content_type": "text",
      "language": "en",
      "meta": {
        "description": "A fantasy adventure novel..."
      }
    }
  ],
  "manifestations": [
    {
      "id": 1,
      "expression_id": 1,
      "isbn13": "9780048230706",
      "upc": null,
      "ean": null,
      "publisher": "Allen & Unwin",
      "publication_date": "1937-09-21",
      "meta": {
        "imageLinks": {},
        "pageCount": 310
      }
    }
  ],
  "items": [
    {
      "id": 1,
      "manifestation_id": 1,
      "owner_id": "user123",
      "status": "available",
      "condition": "good",
      "added_at": "2026-01-15T14:22:00.000000",
      "meta": {
        "location": "Shelf A",
        "notes": "First edition"
      }
    }
  ]
}
```

#### Exporting Data

**Via API:**

```bash
# Export all data
curl -o iqoqo_export.json http://localhost:5000/api/admin/export

# Get database statistics
curl http://localhost:5000/api/admin/stats
```

**Via Python:**

```python
from app import create_app
from app.core.data_manager import DataManager

app = create_app()
with app.app_context():
    # Export to file
    DataManager.export_to_file('backup.json')

    # Or get as dictionary
    data = DataManager.export_all()
```

#### Importing Data

**Via API:**

```bash
# Import data (merge with existing)
curl -X POST -H "Content-Type: application/json" \
     -d @iqoqo_export.json \
     http://localhost:5000/api/admin/import

# Import and clear existing data first
curl -X POST -H "Content-Type: application/json" \
     -d @iqoqo_export.json \
     "http://localhost:5000/api/admin/import?clear_existing=true"

# Import via file upload
curl -X POST -F "file=@iqoqo_export.json" \
     http://localhost:5000/api/admin/import
```

**Via Python:**

```python
from app import create_app
from app.core.data_manager import DataManager

app = create_app()
with app.app_context():
    # Import from file
    counts = DataManager.import_from_file('backup.json')
    print(f"Imported: {counts}")

    # Import from dictionary
    data = {...}
    counts = DataManager.import_data(data, clear_existing=False)
```

#### Migrating from Legacy iqoqo-prototype

If you're migrating from the original iqoqo-prototype, follow these steps:

1. **Export data from your legacy database:**

   If you have a SQL dump file:

   ```bash
   python scripts/sql_to_json.py legacy_dump.sql legacy_data.json
   ```

2. **Migrate the data to FRBR format:**

   ```bash
   python scripts/migrate_legacy.py legacy_data.json --clear
   ```

   The `--clear` flag will remove any existing data before migration.

The migration script automatically:

- Creates Works from book titles (deduplicating by title)
- Creates Expressions for each language/content type
- Converts Manifestations to the new schema
- Maps Items to their new Manifestations
- Preserves all metadata in the `meta` JSON fields

#### Admin API Endpoints

The following endpoints are available for data management:

- `GET /api/admin/stats` - Get database statistics
- `GET /api/admin/export` - Download full database export as JSON
- `POST /api/admin/import` - Import data from JSON (body or file upload)
  - Query param: `clear_existing=true` to clear before import
- `DELETE /api/admin/clear` - Clear all data (requires `{"confirm": true}` in body)

**Security Note:** In a production environment, these admin endpoints should be protected with authentication and authorization. Consider implementing API keys or OAuth for access control.

#### Artefact (Cover) Management

For exporting and importing covers/images (artefacts) between instances, see the **[Cover Generation & Retrieval Setup](COVERS_SETUP.md#6-importing-covers-to-a-remote-iqoqo-instance)** guide.

### Troubleshooting

#### Database Connection Issues

- **`FATAL: role "iqoqo" does not exist`** (stale Docker volume): PostgreSQL only runs its
  initialisation scripts when the data directory is **empty**. If your Docker volume was
  previously created with a different `POSTGRES_USER` value, the `iqoqo` role is never
  created on subsequent starts. Running `./run.sh dev` handles this automatically via
  `scripts/setup_db.sh`. To run the fix manually:

  ```bash
  bash scripts/setup_db.sh
  # or, to just inspect without changing anything:
  bash scripts/setup_db.sh --check
  ```

  The script detects the actual superuser in the volume, creates the `iqoqo` role (if
  missing), and grants all necessary privileges, without touching existing data.

- **`DATABASE_URL` host `db` not resolvable outside Docker**: The hostname `db` is a
  Docker Compose internal service name — it only resolves inside the container network.
  For local development (Flask running directly on the host), use `localhost`:

  ```bash
  # In .env — correct for local dev:
  DATABASE_URL="postgresql://iqoqo:password@localhost:5432/iqoqo"

  # In docker-compose.yml or when running inside a container:
  DATABASE_URL="postgresql://iqoqo:password@db:5432/iqoqo"
  ```

- **Port conflicts**: If you see "port already in use" errors:
  - Check what's using the port: `sudo lsof -i :5432` (database) or `sudo lsof -i :5000` (default `WEB_PORT`, or your configured port, e.g., `:5001`)
  - Change `WEB_PORT` and/or `DB_PORT` in your `.env` file
  - `./run.sh dev` automatically kills stale processes on `WEB_PORT` and `3000` at startup
  - Restart the services: `docker compose down && docker compose up -d`

- **macOS AirPlay Receiver occupies port 5000**: Apple's AirPlay Receiver service binds to port 5000 (the default `WEB_PORT` when not overridden) on macOS Monterey and later. Set `WEB_PORT=5001` (or any other free port) in your `.env` to move Flask off port 5000:

  ```bash
  echo "WEB_PORT=5001" >> .env
  ```

#### Docker Issues

- **Permission denied errors**: If you need to use `sudo` with Docker commands, prefix all `docker` and `docker compose` commands with `sudo`:

  ```bash
  sudo docker compose up -d
  sudo docker compose exec web flask db upgrade
  ```

- **Container won't start**: Check the logs for errors:

  ```bash
  docker compose logs web
  docker compose logs db
  ```

- **Database initialization fails**: Make sure the database container is fully started before running migrations:

#### Frontend Issues

- **`Unable to acquire lock at frontend/.next/dev/lock`**: This happens when a previous
  Next.js dev process crashed or was killed without cleaning up its lock file.
  `./run.sh dev` removes this file automatically at startup. To fix manually:

  ```bash
  rm -f frontend/.next/dev/lock
  # Then restart:
  ./run.sh dev
  ```

- **CORS errors (`Origin ... is not allowed`)**: The Flask CORS configuration must
  list the exact origin of the Next.js dev server. Check your `.env`:

  ```bash
  CORS_ENABLED=true
  CORS_ORIGINS="http://localhost:3000"
  ```

  Also verify `frontend/.env.local` points to the actual Flask port:

  ```bash
  NEXT_PUBLIC_API_URL=http://localhost:5001/api   # match WEB_PORT in .env
  ```

  After editing, clear the Next.js cache and restart: `rm -rf frontend/.next && ./run.sh dev`

  ```bash
  # Wait for database to be ready
  docker compose up -d db
  sleep 5
  docker compose exec web flask db upgrade
  ```

## Running the Application

### Development Mode (Local)

To run the Flask development server:

```bash
# Make sure the database is running
docker compose up -d db

# Run the development server using the project's virtual environment
.venv/bin/flask run
```

**Alternative:** Activate the virtual environment first, then run Flask:

```bash
source .venv/bin/activate
flask run
```

The application will be available at `http://localhost:5000`.

To run the Flask development server:

```bash
# Make sure the database is running
docker compose up -d db

# Run the development server
./run.sh dev
```

**Manual start:**

```bash
flask run
```

The application will be available at `http://localhost:5000`.

### Production Mode (Docker)

For production deployments, use Docker Compose to run the full stack. See [Option B: Full Docker Deployment](#option-b-full-docker-deployment-production) above for complete instructions.

```bash
docker compose up -d
```

Access the application at `http://localhost:{WEB_PORT}` (default: 5000, or 8000 if you changed it in `.env`).

## Data Curation

### Fixing Non-Canonical Format Values

External APIs (TMDB, MusicBrainz, BGG, etc.) return non-canonical physical kind strings
(e.g., `"video"` instead of `"dvd"`, `"audio"` instead of `"cd"`) that are stored in
`Manifestation.meta['format']`. This breaks the Physical Kind facet and the `?format=` filter.

iQoQo provides a three-step workflow to audit and fix these values:

#### 1. Audit

```bash
make fix-physical-kinds
```

This scans the database for all non-canonical and NULL format values and prints a table
with columns: stored value, content type, count, and example titles.

#### 2. Interactive Mapping

```bash
make fix-physical-kinds ARGS="--interactive"
# make fix-physical-kinds ARGS="--interactive" preview
# make fix-physical-kinds ARGS="--interactive" prod
```

Walks you through each distinct non-canonical value, shows example titles for context,
and prompts you to select the correct canonical format. Your selections are written to
`shared/format_mappings.yaml` — a git-tracked YAML file.

Example mapping entries:

```yaml
format_normalizations:
  # Exact value match (any content type)
  video: dvd
  audio: cd
  boardgame: board_game

  # NULL format scoped by content type
  null:
    music: cd
    movie: dvd
    text: book
```

#### 3. Apply

```bash
# Preview changes without modifying the database
make fix-physical-kinds ARGS="--apply --dry-run"

# Apply the fixes
make fix-physical-kinds ARGS="--apply"
```

After applying, non-canonical values are replaced with canonical `MediaFormat` identifiers,
and the Physical Kind facet and `?format=` filter work correctly.

**Important notes:**

- `shared/format_mappings.yaml` is git-tracked and **per-instance** — different
  deployments may map `"video"` to `dvd` or `bluray` depending on their collection.
- Back up your database before running `--apply` (use `make db-export`).
- Items with unresolvable formats are displayed as "Unknown Video Format",
  "Unknown Audio Format", or "Unknown Text Format" in the UI until they are mapped.
- See `shared/format_mappings.yaml` for the complete schema reference.

## Code Quality Checks

Before committing code, ensure quality standards are met:

```bash
# Run all linters
make lint

# Auto-format code
make format

# Run tests
make test
```

### Individual Quality Checks

```bash
# Python
make lint-python    # Ruff + mypy
make format-python  # Black + isort

# JavaScript/CSS
make lint-js        # ESLint
make lint-css       # stylelint

# Markdown
make lint-markdown  # markdownlint
```

## Next Steps

- See **[CHANGELOG.md](CHANGELOG.md)** for the latest updates and release notes.
- See **[CONTRIBUTING.md](CONTRIBUTING.md)** for development guidelines and coding standards.
- See **[ARCHITECTURE.md](ARCHITECTURE.md)** to understand the FRBR hierarchy and data model.
- See **[COVERS_SETUP.md](COVERS_SETUP.md)** for advanced cover art and vision configuration.
- Check **[docs/ontology/iqoqo.ttl](ontology/iqoqo.ttl)** for the FRBR ontology structure.

The application will be available at `http://127.0.0.1:5000`.

## Running Tests

To run the tests, use `pytest`:

```bash
pytest
```

This will discover and run all the tests in the `tests/` directory. The tests are configured to run with an in-memory SQLite database, so you don't need to have PostgreSQL running for the tests.

# Installation Guide

This document provides comprehensive instructions for setting up iqoqo for development and production use.

## Prerequisites

### Required Software

- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Node.js 18+** and **npm** - [Download](https://nodejs.org/)
- **PostgreSQL 15+** - Can be run via Docker (recommended) or installed locally
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

    You can edit the `.env` file to match your local configuration, for example, your database credentials.

    > **Note for VS Code users:** To have the environment variables from the `.env` file automatically loaded in the integrated terminal, you need to enable the `python.terminal.useEnvFile` setting. You can do this by opening your VS Code settings (JSON) and adding `"python.terminal.useEnvFile": true`.

## Database Setup

This project uses PostgreSQL as its database. The easiest way to get a PostgreSQL database running is by using Docker Compose.

1. **Start the database service:**

    ```bash
    docker-compose up -d db
    ```

   This is necessary for the `flask db` commands, which run on the host, to connect to the database. The default credentials are set in the `docker-compose.yml` file and should match the ones in your `.env` file.

2. **Initialize the database:**

    Once the application is set up, you can initialize the database schema using Flask-Migrate:

    ```bash
    flask db init
    flask db migrate -m "Initial migration."
    flask db upgrade
    ```

3. **Initialize with seed data (optional):**

    If you have a JSON export file from a previous iqoqo instance or want to import data:

    ```bash
    python scripts/init_db.py --seed-file path/to/data.json
    ```

    This will only import data if the database is empty.

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

### Troubleshooting

- **`FATAL: role "user" does not exist`**: This error usually means your application is connecting to a different PostgreSQL instance than the one running in Docker.
  - Make sure you have started the Docker container with `docker-compose up -d db`.
  - Check if you have another PostgreSQL server running on your machine on port `5432`. If so, stop it and try again. Here are some common ways to do that:
    - **To check what's using the port:** `sudo lsof -i :5432`
    - **On macOS with Homebrew:** `brew services stop postgresql`
    - **On Ubuntu/Debian with systemd:** `sudo systemctl stop postgresql`
  - Verify that your `.env` file contains the correct `DATABASE_URL` that points to the Dockerized database (`postgresql://user:password@localhost:5432/iqoqo`).

## Running the Application

### Development Mode

**Recommended - Use Make commands:**

```bash
# Start everything (Colima, PostgreSQL, Flask)
make start

# Stop everything cleanly
make stop
```

**Alternative - Use startup script directly:**

```bash
./run_dev.sh
```

**Manual start:**

```bash
# Ensure Colima and database are running
colima start
docker-compose up -d db

# Start Flask
export FLASK_APP=run.py
export FLASK_DEBUG=1
flask run
```

The application will be available at `http://localhost:5000`.

### Production Mode with Docker

To run the full stack (app + database) in production mode:

```bash
docker-compose up
```

This starts both the PostgreSQL database and the Flask application behind Nginx.

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

- See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines
- Read the [API documentation](../README.md#api-documentation) for API usage
- Check [docs/ontology/iqoqo.ttl](ontology/iqoqo.ttl) for the FRBR ontology structure

The application will be available at `http://127.0.0.1:5000`.

## Running Tests

To run the tests, use `pytest`:

```bash
pytest
```

This will discover and run all the tests in the `tests/` directory. The tests are configured to run with an in-memory SQLite database, so you don't need to have PostgreSQL running for the tests.

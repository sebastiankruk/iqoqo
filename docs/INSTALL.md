# Installation Guide

This document provides comprehensive instructions for setting up iqoqo for development and production use.

## Quick Start (Docker)

For the fastest setup, use Docker Compose:

```bash
# 1. Clone and navigate to the repository
git clone https://github.com/sebastiankruk/iqoqo.git
cd iqoqo

# 2. Create and configure environment file
cp .env.example .env
# Edit .env: Set DATABASE_URL to use 'db' hostname, configure ports, set strong passwords

# 3. Build and start services
docker-compose build
docker-compose up -d

# 4. Initialize database
docker-compose exec web flask db upgrade

# 5. (Optional) Load sample data
docker-compose exec web python scripts/init_db.py --seed-file data/seed_example.json

# 6. Access the application
# http://localhost:5000 (or your configured WEB_PORT)
```

For detailed configuration and development setup, continue reading below.

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

   > **Note for VS Code users:** To have the environment variables from the `.env` file automatically loaded in the integrated terminal, you need to enable the `python.terminal.useEnvFile` setting. You can do this by opening your VS Code settings (JSON) and adding `"python.terminal.useEnvFile": true`.

## Database Setup

This project uses PostgreSQL as its database. You have two options:

### Option A: Local Development (Database Only in Docker)

Use this option if you want to run the Flask application on your host machine but use a containerized PostgreSQL database.

1. **Start the database service:**

   ```bash
   docker-compose up -d db
   ```

   This starts only the PostgreSQL container. Make sure your `.env` file has:

   ```text
   DATABASE_URL="postgresql://iqoqo:password@localhost:5432/iqoqo"
   ```

2. **Initialize the database:**

   Once the application is set up, you can initialize the database schema using Flask-Migrate:

   ```bash
   flask db upgrade
   ```

3. **Initialize with seed data (optional):**

   If you have a JSON export file from a previous iqoqo instance or want to import data:

   ```bash
   python scripts/init_db.py --seed-file path/to/data.json
   ```

   This will only import data if the database is empty.

### Option B: Full Docker Deployment (Production)

Use this option to run both the Flask application and PostgreSQL database in containers. This is the recommended approach for production deployments.

1. **Configure environment variables:**

   Make sure your `.env` file is configured for Docker:

   ```bash
   # Use 'db' as hostname for container-to-container communication
   DATABASE_URL="postgresql://iqoqo:your_password@db:5432/iqoqo"

   # Set external ports (change if you have other services running)
   WEB_PORT=8000    # or 5000 if available
   DB_PORT=5433     # or 5432 if available

   # Use production settings
   FLASK_ENV=production
   ```

2. **Build and start all services:**

   ```bash
   # Build the application image
   docker-compose build

   # Start all services (web + database)
   docker-compose up -d
   ```

   If you need to use `sudo` with Docker:

   ```bash
   sudo docker compose build
   sudo docker compose up -d
   ```

3. **Initialize the database:**

   Run migrations inside the web container:

   ```bash
   docker-compose exec web flask db upgrade
   ```

   Or with sudo:

   ```bash
   sudo docker compose exec web flask db upgrade
   ```

4. **Initialize with seed data (optional):**

   ```bash
   docker-compose exec web python scripts/init_db.py --seed-file data/seed_example.json
   ```

5. **Verify deployment:**

   ```bash
   # Check container status
   docker-compose ps

   # View logs
   docker-compose logs -f web

   # Test the application
   curl http://localhost:8000/  # Use your WEB_PORT
   ```

The application will be available at `http://localhost:8000` (or whatever port you configured as `WEB_PORT`).

#### Docker Management Commands

```bash
# View logs
docker-compose logs -f web    # Follow web application logs
docker-compose logs -f db     # Follow database logs

# Restart services
docker-compose restart web
docker-compose restart db

# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ this deletes all database data!)
docker-compose down -v

# Rebuild after code changes
docker-compose build
docker-compose up -d

# Execute commands in containers
docker-compose exec web flask db upgrade
docker-compose exec db psql -U iqoqo -d iqoqo

# View running containers and resource usage
docker-compose ps
docker stats --no-stream
```

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

#### Database Connection Issues

- **`FATAL: role "user" does not exist`**: This error usually means your application is connecting to a different PostgreSQL instance than the one running in Docker.
  - Make sure you have started the Docker container with `docker-compose up -d db`.
  - Check if you have another PostgreSQL server running on your machine. If so, either:
    - Stop the local PostgreSQL: `brew services stop postgresql` (macOS) or `sudo systemctl stop postgresql` (Linux)
    - Change the `DB_PORT` in your `.env` file to use a different port (e.g., 5433)
  - Verify that your `.env` file contains the correct `DATABASE_URL`:
    - For local development: `postgresql://iqoqo:password@localhost:5432/iqoqo`
    - For Docker deployment: `postgresql://iqoqo:password@db:5432/iqoqo`

- **Port conflicts**: If you see "port already in use" errors:
  - Check what's using the port: `sudo lsof -i :5432` or `sudo lsof -i :5000`
  - Change `WEB_PORT` and/or `DB_PORT` in your `.env` file
  - Restart the services: `docker-compose down && docker-compose up -d`

#### Docker Issues

- **Permission denied errors**: If you need to use `sudo` with Docker commands, prefix all `docker` and `docker-compose` commands with `sudo`:

  ```bash
  sudo docker compose up -d
  sudo docker compose exec web flask db upgrade
  ```

- **Container won't start**: Check the logs for errors:

  ```bash
  docker-compose logs web
  docker-compose logs db
  ```

- **Database initialization fails**: Make sure the database container is fully started before running migrations:

  ```bash
  # Wait for database to be ready
  docker-compose up -d db
  sleep 5
  docker-compose exec web flask db upgrade
  ```

## Running the Application

### Development Mode (Local)

To run the Flask development server on your host machine (with database in Docker):

```bash
# Make sure the database is running
docker-compose up -d db

# Run the development server
./run_dev.sh
```

Or manually:

```bash
source .venv/bin/activate
flask run
```

The application will be available at `http://localhost:5000`.

### Production Mode (Docker)

For production deployments, use Docker Compose to run the full stack. See [Option B: Full Docker Deployment](#option-b-full-docker-deployment-production) above for complete instructions.

```bash
docker-compose up -d
```

Access the application at `http://localhost:{WEB_PORT}` (default: 5000, or 8000 if you changed it in `.env`).

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

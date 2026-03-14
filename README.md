# iqoqo — The Library of Everything

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Next.js Version](https://img.shields.io/badge/Next.js-16%2B-black.svg)](https://nextjs.org/)
[![Node.js Version](https://img.shields.io/badge/Node.js-18%2B-green.svg)](https://nodejs.org/en/)
[![Flask Version](https://img.shields.io/badge/Flask-2.3%2B-green.svg)](https://flask.palletsprojects.com/en/latest/)
[![Python Version](https://img.shields.io/badge/Python-3.14%2B-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL Version](https://img.shields.io/badge/PostgreSQL-15%2B-blue.svg)](https://www.postgresql.org/)

**iqoqo** is a distributed, semantic, and federated library system designed to catalog physical and digital collections—spanning books, vinyl, board games, and beyond.

Unlike "flat" catalogs, iqoqo is built on the **FRBR (Functional Requirements for Bibliographic Records)** ontology, allowing for a deep understanding of the relationship between a *Work* (e.g., "The Hobbit"), its *Expression* (the English text), its *Manifestation* (the 1937 hardcover), and your specific *Item* (the copy on your shelf).

## 🚀 Key Features

- **Semantic Core:** Deep metadata support via FRBRoo and JSON-LD.
- **Federated Discovery:** Search your own collection or the wider iqoqo network while maintaining data sovereignty.
- **Barcode & Cover Scanning:** Rapidly add items via ISBN/EAN integration.
- **API-First:** Built with a Flask REST API, ready for Web, Android, and iOS.
- **Linked Open Data:** Every item is a URI, ready for the Semantic Web.
- **Privacy First:** You own your data; you decide what to share with the "cloud."

## 🛠 Tech Stack

- **Frontend:** Next.js 16 / TypeScript / Tailwind CSS
- **Backend:** Python 3.14+ / Flask
- **Database:** PostgreSQL (with Full-Text Search and JSONB)
- **Deployment:** Docker & Docker Compose

## � Quick Start

Get iqoqo running in minutes with Docker:

```bash
# Clone the repository
git clone https://github.com/sebastiankruk/iqoqo.git
cd iqoqo

# Configure environment (edit .env after copying)
cp .env.example .env

# Start with Docker Compose
docker-compose build
docker-compose up -d

# Initialize database
docker-compose exec web flask db upgrade

# Access at http://localhost:5000
```

For detailed installation instructions, port configuration, and development setup, see the [Installation Guide](docs/INSTALL.md).

### CORS Configuration

CORS is disabled by default and should be enabled only when the frontend is served from a different origin than the API.

Configure via environment variables in `.env`:

```text
CORS_ENABLED=true
CORS_ORIGINS="https://app.example.com,https://admin.example.com"
CORS_SUPPORTS_CREDENTIALS=false
```

Use explicit origins in production (avoid wildcard origins). Enable `CORS_SUPPORTS_CREDENTIALS=true` only when required.

## �📖 Documentation

- **[Installation Guide](docs/INSTALL.md)** - Complete setup instructions including data migration
- **[Architecture Guide](docs/ARCHITECTURE.md)** - FRBR hierarchy explained with code examples
- **[Contributing Guide](docs/CONTRIBUTING.md)** - Development workflow and coding standards
- **[FRBR Ontology](docs/ontology/iqoqo.ttl)** - The semantic model powering iqoqo

## 📦 Data Management

iqoqo provides comprehensive tools for data import, export, and migration:

### Quick Start with Seed Data

```bash
# Initialize database with example books
python scripts/init_db.py --seed-file data/seed_example.json
```

### Export Your Library

```bash
# Via API
curl -o my_library.json http://localhost:5000/api/admin/export

# Or via Python
python -c "from app import create_app; from app.core.data_manager import DataManager; \
app = create_app(); \
with app.app_context(): DataManager.export_to_file('my_library.json')"
```

### Import Data

```bash
# Via API
curl -X POST -F "file=@my_library.json" http://localhost:5000/api/admin/import

# Via script
python scripts/init_db.py --seed-file my_library.json
```

See the [Installation Guide](docs/INSTALL.md#data-importexport) for detailed documentation.

## 🎯 Roadmap

- [x] Admin web UI for data management
- [x] Multi-user authentication and authorization
- [ ] Federation protocol for cross-instance discovery
- [ ] Mobile apps (iOS & Android)
- [ ] Advanced search with SPARQL queries
- [ ] Collection sharing and social features

## 📜 License

## License

This project is licensed under the [GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later)](LICENSE).

## 🙏 Acknowledgments

Built on the shoulders of giants: FRBR, Linked Data, and the Semantic Web community.

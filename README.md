# iqoqo — The Library of Everything

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

- **Frontend:** React, Next.js (App Router), TypeScript, Tailwind CSS
- **Backend:** Python 3.11+ / Flask
- **Database:** PostgreSQL (with Full-Text Search and JSONB)
- **Ontology:** RDFLib / FRBR
- **Deployment:** Docker & Docker Compose

## 🚀 Quick Start

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

# Access at http://localhost:3000 (Frontend) and http://localhost:5000 (API)
```

For detailed installation instructions, port configuration, and development setup, see the [Installation Guide](docs/INSTALL.md).

### CORS Configuration

CORS is disabled by default and should be enabled only when the frontend is served from a different origin than the API.

Configure via environment variables in `.env`:

```env
CORS_ENABLED=true
CORS_ORIGINS=https://app.example.com,https://admin.example.com
CORS_SUPPORTS_CREDENTIALS=false
```

Use explicit origins in production (avoid wildcard origins). Enable `CORS_SUPPORTS_CREDENTIALS=true` only when required.

## 📖 Documentation

- **[Installation Guide](docs/INSTALL.md)** - Complete setup instructions including data migration
- **[Phase 4 Ubuntu Cutover](docs/PHASE4_UBUNTU_CUTOVER.md)** - Deployment runbook for switching to frontend+API+nginx
- **[Architecture Guide](docs/ARCHITECTURE.md)** - FRBR hierarchy explained with code examples
- **[Contributing Guide](docs/CONTRIBUTING.md)** - Development workflow and coding standards
- **[FRBR Ontology](docs/ontology/iqoqo.ttl)** - The semantic model powering iqoqo

## 📦 Data Management

iqoqo provides comprehensive tools for data import, export, and migration:

### Quick Start with Seed Data

```markdown
# Initialize database with example books
python scripts/init_db.py --seed-file data/seed_example.json
```

### Export Your Library

```markdown
# Via API
curl -o my_library.json http://localhost:5000/api/admin/export

# Or via Python
python -c "from app import create_app; from app.core.data_manager import DataManager; \
app = create_app(); \
with app.app_context(): DataManager.export_to_file('my_library.json')"
```

### Import Data

```markdown
# Via API
curl -X POST -F "file=@my_library.json" http://localhost:5000/api/admin/import

# Via script
python scripts/init_db.py --seed-file my_library.json
```

### Migrate from Legacy iqoqo-prototype

If you're migrating from the original iqoqo-prototype:

```markdown
# 1. Convert SQL dump to JSON
python scripts/sql_to_json.py legacy_dump.sql legacy_data.json

# 2. Migrate to FRBR format
python scripts/migrate_legacy.py legacy_data.json --clear
```

See the [Installation Guide](https://www.google.com/search?q=docs/INSTALL.md%23data-importexport) for detailed documentation.

## 🎯 Roadmap

- [ ] Admin web UI for data management
- [ ] Multi-user authentication and authorization
- [ ] Federation protocol for cross-instance discovery
- [ ] Mobile apps (iOS & Android)
- [ ] Advanced search with SPARQL queries
- [ ] Collection sharing and social features

## 📜 License

MIT License - see [LICENSE](https://www.google.com/search?q=LICENSE) for details.

## 🙏 Acknowledgments

Built on the shoulders of giants: FRBR, Linked Data, and the Semantic Web community.

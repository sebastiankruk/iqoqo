# iqoqo — The Library of Everything

**iqoqo** is a distributed, semantic, and federated library system designed to catalog physical and digital collections—spanning books, vinyl, board games, and beyond.

Unlike "flat" catalogs, iqoqo is built on the **[FRBR (Functional Requirements for Bibliographic Records)](https://www.ifla.org/publications/functional-requirements-for-bibliographic-records/)** ontology, allowing for a deep understanding of the relationship between a *Work* (e.g., "The Hobbit"), its *Expression* (the English text), its *Manifestation* (the 1937 hardcover), and your specific *Item* (the copy on your shelf).

## 🚀 Key Features

- **Semantic Core:** Deep metadata support via **[FRBRoo](https://www.cidoc-crm.org/frbroo/home-0)** and **[JSON-LD](https://json-ld.org/)**.
- **Federated Discovery:** Search your own collection or the wider iqoqo network while maintaining data sovereignty.
- **Barcode & Cover Scanning:** Rapidly add items via ISBN/EAN integration.
- **API-First:** Built with a Flask REST API, ready for Web, Android, and iOS.
- **Linked Open Data:** Every item is a URI, ready for the **[Semantic Web](https://www.w3.org/standards/semanticweb/)**.
- **Privacy First:** You own your data; you decide what to share with the "cloud."

## 🛠 Tech Stack

- **Frontend:** React, Next.js (App Router), TypeScript, Tailwind CSS
- **Backend:** Python 3.14+ / Flask
- **Database:** PostgreSQL (with Full-Text Search and JSONB)
- **Ontology:** RDFLib / FRBR
- **Computer Vision:** OpenCV / NumPy (Optional/Experimental)
- **Deployment:** Docker & Docker Compose
- **Networking:** Cloudflare Tunnel (for dev-server sharing)

## 📖 Documentation

- **[Installation Guide](docs/INSTALL.md)** - Complete setup instructions including data migration
- **[Architecture Guide](docs/ARCHITECTURE.md)** - FRBR hierarchy explained with code examples
- **[Contributing Guide](docs/CONTRIBUTING.md)** - Development workflow and coding standards
- **[Changelog](docs/CHANGELOG.md)** - Recent updates and version history
- **[Cover Setup](docs/COVERS_SETUP.md)** - AI cover generation and vision extraction setup
- **[FRBR Ontology](docs/ontology/iqoqo.ttl)** - The semantic model powering iqoqo

## 🚀 Quick Start

Get iqoqo running in minutes with Docker:

```bash
# 1. Clone the repository
git clone https://github.com/sebastiankruk/iqoqo.git
cd iqoqo

# 2. Configure environment
cp .env.example .env

# 3. Start services
docker compose up -d
```

For detailed installation, port configuration, and seed data initialization, see the **[Installation Guide](docs/INSTALL.md)**.

## 📦 Data & Artefact Management

iqoqo provides comprehensive tools for managing your library's data and media assets:

- **Data Import/Export:** Export your catalog to JSON or import from other instances. See **[Data Import/Export](docs/INSTALL.md#data-importexport)**.
- **Artefact Management:** Backup or transfer cover art and generated images. See **[Importing Covers](docs/COVERS_SETUP.md#6-importing-covers-to-a-remote-iqoqo-instance)**.
- **Seed Data:** Initialize your library with example books. See **[Quick Start Data](docs/INSTALL.md#quick-start-docker)**.

## 🎯 Roadmap

- [x] Multi-user authentication and authorization
- [x] Support for different types of media (books, vinyl, board games, etc.)
- [ ] Admin web UI for data management
- [ ] Federation protocol for cross-instance discovery
- [ ] Mobile apps (iOS & Android)
- [ ] Advanced search with SPARQL queries
- [ ] Collection sharing and social features

## 📜 License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0-only). See [LICENSE](LICENSE) for full details.

## 🙏 Acknowledgments

Built on the shoulders of giants: FRBR, Linked Data, and the Semantic Web community.

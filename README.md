# iqoqo — The Library of Everything

<img src="resources/images/iqoqo-logo.svg" alt="iqoqo logo" width="200" class="iqoqo-logo">

<div align="center">

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub-EA4AAA.svg?style=flat&logo=github-sponsors&logoColor=white)](https://github.com/sponsors/sebastiankruk)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-Support-FFDD00.svg?style=flat&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/iqoqo)

[![Python Version](https://img.shields.io/badge/Python-3.14%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Flask Version](https://img.shields.io/badge/Flask-3.1-black.svg?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Next.js Version](https://img.shields.io/badge/Next.js-16.2-black.svg?logo=next.js&logoColor=white)](https://nextjs.org/)
[![React Version](https://img.shields.io/badge/React-19.2-61DAFB.svg?logo=react&logoColor=black)](https://react.dev/)
[![Tailwind CSS Version](https://img.shields.io/badge/Tailwind_CSS-v4-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![TypeScript Version](https://img.shields.io/badge/TypeScript-5.0-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![PostgreSQL Version](https://img.shields.io/badge/PostgreSQL-16-336791.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-red.svg)](LICENSE)

</div>

**iqoqo** is a distributed, semantic, and federated library system designed to catalog physical and digital collections—spanning books, vinyl, board games, and beyond.

Unlike "flat" catalogs, iqoqo is built on the **[FRBR (Functional Requirements for Bibliographic Records)](https://www.ifla.org/publications/functional-requirements-for-bibliographic-records/)** ontology, allowing for a deep understanding of the relationship between a _Work_ (e.g., "The Hobbit"), its _Expression_ (the English text), its _Manifestation_ (the 1937 hardcover), and your specific _Item_ (the copy on your shelf).

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
- [x] Admin web UI for data management
- [x] Socializing collections with sharing and recommendations
- [ ] Mobile apps (iOS & Android)
- [ ] Federation protocol for cross-instance discovery
- [ ] Advanced search with SPARQL queries

## 💖 Support & Upstream Sustainability

iqoqo is, and always will be, free and open-source software. However, maintaining the infrastructure, running global semantic validation tests, and paying localized gatekeeper tolls (such as the annual Apple Developer Program fee to allow distributed mobile PWA configurations or standalone builds) costs money.

If you find value in this project or are running a public deployment for your community, please consider backing the upstream development ecosystem:

- **GitHub Sponsors:** [Sponsor on GitHub](https://github.com/sponsors/sebastiankruk) (Best for recurring developer support)
- **Buy Me a Coffee:** [Support on Buy Me a Coffee](https://buymeacoffee.com/iqoqo) (Best for quick, one-off micro-donations)

Your support directly covers operational toll fees to keep target deployment channels open and unencumbered.

## 📜 License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0-only). See [LICENSE](LICENSE) for full details.

## 🤠 The iqoqo Gathering: Silicon & Soul

<img src="resources/images/iqoqo-team.gif" alt="the iqoqo gathering" width="700" class="iqoqo-git">

> Deep in the heart of the digital savannah at dusk—amidst the glow of retro-neon oranges, purples, and deep blues—lives a tribe of retro digital hunter-gatherers. Under the shade of blocky, LED-lit Baobab trees and circular thatched-roof "Database" kraals, this team works tirelessly to organize and protect the world's cultural metadata.

Meet the crew ke the **iqoqo** fires burning:

| Character             |     Role     | G                                                     | A                                                | Tribal Duty                                                      |
|-----------------------|:------------:|-------------------------------------------------------|--------------------------------------------------|------------------------------------------------------------------|
| **Sebastian**         | The Inventor |                                                       |                                                  | The mastermind raven guiding the flock.                          |
| **Batch-One Penny**   |   Product    | [G](.gemini/gems/product-manager.md)                  |                                                  | Keeping the sprints on schedule and batches rolling.             |
| **Sidekick Silas**    |    Coding    | [G](.gemini/gems/software-engineer.md)                | [A](.agents/workflows/implementator.md)          | Spinning coffee and prompt tokens into clean Next.js/Flask code. |
| **Red-Team Ricky**    |      QA      | [G](.gemini/gems/quality-assurance.md)                | [A](.agents/workflows/test-automation-wizard.md) | Smashin' pesky crawler bugs before they reach prod.              |
| **Sam Semantic**      |  Ontologist  | [G](.gemini/gems/information-architect-ontologist.md) | [A](.agents/workflows/ontologist.md)             | Ensuring absolute FRBR-compliant database purity.                |
| **Density Denise**    |    UX/UI     | [G](.gemini/gems/ux-expert.md)                        | [A](.agents/workflows/ux-audit.md)               | Aligning the pixel grids so the interface feels like home.       |
| **White-Hat Wally**   |   Security   | [G](.gemini/gems/security-and-stability.md)           | [A](.agents/workflows/security-auditor.md)       | Outsmarting SSRF and locking out unauthenticated crawlers.       |
| **SRE Stan**          |    DevOps    | [G](.gemini/gems/site-reliability-engineering.md)     | [A](.agents/workflows/sre-expert.md)             | Tuning the PostgreSQL connection pools and Celery queues.        |
| **Doc Architect Dan** |   TechComm   | [G](.gemini/gems/technical-communications.md)         | [A](.agents/workflows/tech-comm.md)              | Documenting the tribal laws, API specs, and schemas.             |
| **Growth Gabe**       |  Marketing   | [G](.gemini/gems/launch-and-growth.md)                | [A](.agents/workflows/growth-strategist.md)      | Spreading the word of data ownership to the masses.              |

---

### Tribal Lore & Capabilities

> _"We don't build flat libraries. We map the conceptual soul of media."_

- **Local-First Sovereignty:** This tribe rejects corporate clouds. Your data stays in your self-hosted Kraal (`docker-compose`).
- **Semantic Precision:** Guided by the **FRBR** star, we separate the abstract _Work_ from the physical _Item_.
- **The Hunt for Metadata:** Armed with cascading API strategies, our scanners track down missing records across the digital wilderness.

## 🙏 Acknowledgments

Built on the shoulders of giants: FRBR, Linked Data, and the Semantic Web community.

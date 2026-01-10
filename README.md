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

- **Backend:** Python 3.11+ / Flask
- **Database:** PostgreSQL (with Full-Text Search and JSONB)
- **Ontology:** RDFLib / FRBRoo
- **Deployment:** Docker & Docker Compose

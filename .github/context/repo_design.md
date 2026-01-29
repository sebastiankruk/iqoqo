# Project iQoQo Design Repo and Hosting

## Question 1

analyze project design/requirements and current draft version (with example database of books) and tell me:

- what could be probably? carried over to the new (version?) of this project, e.g., bar code reader?
- how to best approach current github repo - should we create a new one with new name, do some renaming?
- should we stay with iqoqo (I recall was "collect" or "gather" in some african language) or come up with a new one
- what would be the best / cheapest option to register and host domain where main project website, ontologies, etc. should be kept... as we assume that there will be multiple iqoqo instances running in federation hosted by users themselves - allowing them to control what level of details is shared with the "cloud"

iqoqo coding sidekick

Custom Gem

This is an exciting project. Building a distributed, semantic library system ("Library of Everything") on the FRBR (Functional Requirements for Bibliographic Records) model is a sophisticated approach that solves the "flat data" problem of traditional catalogs.

Here is the analysis and roadmap based on the feasibility study, source code, and database dump provided.

### 1. What to Carry Over to the New Version?

Based on the code analysis, you should adopt a **"Logic Reuse, Architecture Rewrite"** strategy. The current draft is a monolithic Flask app with a flat SQL schema, whereas your goal is a semantic, distributed system.

- **Barcode & ISBN Logic (High Value):**
  - **Keep:** The core logic in `py/barcode.py` (using `pyzbar` and `opencv`) and `py/manifestation.py` (ISBN lookup via `isbnlib`) is solid.  
  - **Adapt:** Currently, `py/webcam.py` captures video from the *server's* USB camera. For a Web UI/App distributed to users, you need **client-side scanning**. You should move the scanning logic to the frontend (using JavaScript libraries like `html5-qrcode` mentioned in your `README.md`) or allow the Python backend to process *uploaded images* from a phone's camera, rather than streaming video directly to the server.
- **Database Data (Migration):**
  - **Keep:** The data in `iqoqo.manifestation` (ISBN, Title, Authors) and `iqoqo.item` is valuable.
  - **Migrate:** You cannot use the old schema. You must write a migration script (`ETL`) that transforms this flat data into the FRBR ontology:
    - `manifestation.title` & `authors` **FRBR Work/Expression**.
    - `manifestation.isbn` & `publisher` **FRBR Manifestation**.
    - `item` table rows **FRBR Item**.
- **Feasibility Study & Docs:**
  - **Keep:** The `feasibility study` is excellent. It already defines your stack (Python/Flask/PostgreSQL) and the "Open Core" business model. Use this as your Product Requirements Document (PRD).

### 2. GitHub Repository Strategy

**Recommendation: Create a New Repository.**

- **Clean Slate:** The current repo structure reflects an early prototype with flat SQL files and mixed responsibilities. A distributed, semantic project requires a cleaner structure (e.g., separating the Ontology definitions, the Federation logic/ActivityPub, and the Web UI).
- **Organization:** Create a GitHub Organization (e.g., `github.com/iqoqo-project`) and create a new repo `iqoqo-core` or simply `iqoqo`.
- **Reference:** Keep the old repo read-only as `iqoqo-prototype` for reference. This prevents legacy code confusion while preserving the history of your research.

### 3. Naming: "iqoqo"

**Verdict: STAY with "iqoqo".**

- **Meaning:** You are correct; *iqoqo* means **"collection"** or **"group"** in Zulu (and related Nguni languages). This fits your "Library of Everything" vision perfectly—it is a collection of collections.
- **Branding:** It is short, distinct, symmetrical, and consistent with the "ubuntu" (humanity/community) philosophy often associated with open-source projects.
- **Uniqueness:** It is likely available as a clean `.org` or `.io` domain compared to generic English terms.

### 4. Hosting & Domain Strategy (Federated Model)

Since this is a federated project (users host their own instances), your "Cloud" infrastructure has two distinct roles: **Identity/Discovery** (the project home) and **Ontology Hosting** (the semantic standard).

**Cheapest & Best "Project Home" Option:**

- **Domain Registration:**
  - **Namecheap** or **Cloudflare** are reliable and cost-effective (~$10-15/year). Avoid "first year free" traps from others.
- **Static Website & Docs (The "Project" site):**
  - **GitHub Pages (Free):** Host the marketing site, documentation, and the installer scripts here. It supports custom domains (`iqoqo.org`) and free SSL.
  - *Why:* It handles high traffic for free and integrates with your code.
- **Ontology Hosting (Critical for Semantic Web):**
  - **w3id.org (Free):** Do **not** host ontology namespace URIs directly on a raw domain if you can avoid it. Register a permanent identifier with **w3id.org** (a free service for the semantic web community).
  - *How it works:* You define `https://w3id.org/iqoqo/` which permanently redirects to your GitHub Pages raw file (e.g., `iqoqo.ttl`). This ensures that even if you change hosting providers later, your semantic linked data never breaks.
- **Federation/Discovery Server (Optional):**
  - If you need a central "directory" of public libraries, a small **VPS (Hetzner Cloud or DigitalOcean)** (~$5/mo) running a lightweight Flask app is sufficient. This gives you full control over the "phonebook" of federated instances without managing user data.

### Summary Plan

1. **Repo:** Create new `iqoqo` repo.
2. **Stack:** Python Flask + RDFLib (for FRBR) + PostgreSQL (with JSON-LD storage).
3. **Migration:** Write a script to convert the `combined_output.txt` SQL dump into RDF triples (FRBRoo) for the new system.
4. **Hosting:** Buy domain Set up w3id.org Host site on GitHub Pages.

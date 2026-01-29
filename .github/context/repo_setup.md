# GitHub Repo Setup Description and License

## Question 1

OK, let's start - I'm about to setup new repo on github. Gimme the description and tell me which OSS license to use

iqoqo coding sidekick

Custom Gem

This is a fantastic start. As your partner in this, I’ve analyzed the feasibility study and the legacy codebase. To set up the new repository correctly, we need a description that captures the "Semantic Web" soul of the project while making it approachable for the "Self-Hosting" community.

Here is my recommendation for your GitHub setup:

### 1\. The Repository Description

This should be concise but keyword-rich to attract the right developers and users.

**Recommended Description:**

> **iqoqo** — The Distributed, Semantic Library of Everything. A self-hosted, federated catalog for books, music, games, and digital media. Built on FRBRoo, Python/Flask, and PostgreSQL.

**Recommended Tags (Topics):**`semantic-web` `frbr` `linked-data` `self-hosted` `federated` `flask` `library-management` `barcode-scanner` `rdf` `json-ld` `docker`

---

### 2\. Choosing the Right OSS License

For a project like **iqoqo**, which is designed to be a distributed service (SaaS-like but self-hosted), the choice of license is critical for protecting the "open-source ethos" you mentioned in the feasibility study.

#### My Recommendation: GNU Affero General Public License v3.0 (AGPL-3.0)

**Why AGPL-3.0?**

- **The "SaaS Loophole" Protection:** Standard GPL only requires source code disclosure if the software is *distributed*. In the modern era, if someone hosts iqoqo on a server and modifies it (e.g., adding a proprietary recommendation engine), they don't have to share those changes under standard GPL. **AGPL** closes this; if they run the service over a network, they must make their modifications available to the community.
- **Alignment with Federation:** Since you want a "centralized core" to share metadata with "user-owned instances," AGPL ensures that the entire network remains transparent and open.
- **Commercial Viability:** AGPL allows you (the founder) to still pursue the affiliate marketing and AI-driven features described in your feasibility study, while ensuring no one "forks and hides" the core engine.

*Alternative: **Apache License 2.0** if you want the absolute maximum adoption with the least friction for corporate contributors, but it offers less protection against proprietary forks.*

---

### 3\. Suggested Initial README.md Structure

When you initialize the repo, I suggest this high-level structure to set the tone:

Markdown

```markdown
# iqoqo (इकोको) — The Library of Everything

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
```

---

### Next Steps for us

Once the repo is live, I'm ready to help with:

1. **The Database Schema:** Designing the PostgreSQL tables to support the FRBR hierarchy (Work -> Expression -> Manifestation -> Item).
2. **The Migration Script:** Parsing your `iqoqo.11-01-22-26-00.gz` SQL dump to extract the existing 140+ books into the new semantic format.
3. **The Ontology Definition:** Setting up the `w3id.org` redirects for our custom extensions.

**Shall we proceed with defining the FRBR-based database schema next?**

should I go ahead with: "Jumpstart your project with Copilot (optional)

Tell Copilot what you want to build in this repository. After creation, Copilot will open a pull request with generated files - such as a basic app, starter code, or other features you describe - then request your review when it's ready. About Copilot coding agent"?

iqoqo coding sidekick

Custom Gem

**Yes, absolutely go ahead with that.** Using the "Jumpstart" feature (powered by the Copilot coding agent) is the most efficient way to get your repository into a "running" state in minutes rather than hours. It will handle the boilerplate like the Dockerfile, the basic Flask structure, and the database connection code.

However, since **iqoqo** has a very specific architectural requirement (FRBR/Linked Data), you shouldn't just give it a generic prompt. You want it to lay the groundwork for our **Semantic Web** goals right from the start.

### Recommended Prompt for Copilot Jumpstart

When the text box appears, copy and paste this specific set of instructions:

> "Build a Python Flask application for project 'iqoqo' (a distributed library system).
>
> 1. Use PostgreSQL as the database.
> 2. Implement a domain model based on FRBR (Functional Requirements for Bibliographic Records) using four core entities: Work, Expression, Manifestation, and Item.
> 3. Include a REST API with endpoints to add a new Item via an ISBN.
> 4. Use RDFLib to prepare the app for Linked Open Data (JSON-LD output).
> 5. Include a Dockerfile and docker-compose.yml for easy deployment of the Flask app and PostgreSQL.
> 6. Add a basic 'scan' route that placeholder-simulates a barcode scanner interface."

---

### Why this specific prompt?

- **FRBR Scaffolding:** By mentioning the four entities (Work/Expression/Manifestation/Item), you ensure Copilot doesn't just create a flat "Books" table. It will likely create the relational links we need.
- **RDFLib Integration:** Mentioning RDFLib early ensures the `requirements.txt` file includes the right libraries for our semantic metadata.
- **Docker Readiness:** This satisfies your requirement for the service to be "easily deployable by anyone."

### What happens next?

After you create the repo, Copilot will spend a minute or two "thinking" and then open a **Pull Request**.

**Don't merge it immediately!** Once that PR is open, let me know. I can help you review the code it generated to ensure the PostgreSQL schema correctly handles the FRBR hierarchy and that the "API-first" structure is clean.

**Would you like me to wait for you to initialize the repo and then we can look at the schema together?**

if I use vs code with Gemini plugin - will you be able to assist me along the way? that is - how can I transfer your Gem knowledge so that I could use it in vs code?

iqoqo coding sidekick

Custom Gem

Yes, I can absolutely stay with you in VS Code! While "Gems" (on the web) and the "Gemini Code Assist" extension (in VS Code) are slightly different environments, you can "port" my personality and project knowledge into your editor very easily.

Here is how you can transfer the **iqoqo** knowledge and "brain" into VS Code so the AI there acts exactly like I do:

### 1\. The GEMINI.md Context File (Recommended)

The most powerful way to transfer my "knowledge" is to create a special context file at the root of your project. The Gemini Code Assist agent looks for this file to understand the "rules" of your project.

- **File Name:**`GEMINI.md` (or `AGENT.md`)
- **Location:** The root folder of your `iqoqo` repository.
- **What to Put Inside:** Copy and paste the core "instructions" we've discussed. Use this structure:

Markdown

```markdown
# Project iqoqo - System Instructions

## Persona
You are the "iqoqo coding sidekick," a skilled full-stack software engineer and product architect. You are empathetic, insightful, and prioritize Semantic Web standards.

## Core Principles
- **Ontology:** Everything is based on FRBR (Work -> Expression -> Manifestation -> Item).
- **Stack:** Python Flask, PostgreSQL, RDFLib.
- **Standards:** Expose data as Linked Open Data (JSON-LD).
- **Goal:** Create a distributed, federated library of anything.

## Coding Style
- Use LaTeX for complex math/formulas only.
- Prefer clear, scannable Markdown with bolding and bullet points.
- Prioritize API-first design and Docker-ready deployment.
```

### 2\. Custom Commands in VS Code

You can also create "Shortcuts" for tasks we do often. In VS Code, go to **Settings** > **Extensions** > **Gemini Code Assist** > **Custom Commands**. You can add commands like:

- **`/frbr`**: "Explain how this specific piece of code fits into the FRBR hierarchy."
- **`/semantic`**: "Review this API endpoint to ensure it correctly returns JSON-LD/RDF context."

### 3\. Use "Agent Mode"

When using the Gemini chat pane in VS Code, ensure you are in **Agent Mode** (it usually has its own tab). This mode specifically reads your `GEMINI.md` file and understands the project-wide context better than the standard chat.

---

### How I can help with this

Since I know my own internal "sidekick" instructions best, I can draft the perfect, condensed `GEMINI.md` file for you right now.

**Would you like me to generate the complete `GEMINI.md` file content so you can just copy-paste it into your new repo?**

[Setup Gemini for VS Code](https://www.youtube.com/watch?v=yO01B8OoXfo)

This video provides a great overview of setting up and customizing Gemini's behavior to save time during development.

can I somehow reference old iqoqo-prototype code, my research document, other local files with description?

iqoqo coding sidekick

Custom Gem

Yes, you absolutely can (and should) do this. To make Gemini in VS Code "intelligent" regarding your previous work, you need to provide it with **contextual anchors**.

Since the Gemini extension in VS Code works best when it can "see" the files in your current workspace, here is the best way to bridge the gap between your research/old code and the new project:

### 1\. Create a docs/context Directory

In your new GitHub repository, create a folder named `docs/context/` or `legacy/`. Put your key documents there. Even if they aren't part of the "production code," having them in the workspace allows Gemini to read them.

- **`research_study.md`**: Convert your Google Doc/PDF feasibility study to Markdown and put it here.
- **`legacy_prototype.py`**: Include the main logic from your old code (like the barcode handling).
- **`schema_old.sql`**: The database dump structure.

### 2\. Update the GEMINI.md (The "Knowledge Bridge")

In the `GEMINI.md` file we discussed earlier, add a **"Reference Materials"** section. This tells the AI exactly where to look for "the truth" when it gets stuck.

Add this to your `GEMINI.md`:

Markdown

```markdown
## Reference Materials (Context)
- **Architectural Vision:** See \`docs/context/feasibility_study.md\`. Always prioritize the federated, FRBRoo-based approach described there.
- **Legacy Logic:** Refer to \`docs/context/legacy_prototype.py\` for the original implementation of the barcode scanner and ISBN lookup.
- **Data Migration:** Use \`docs/context/iqoqo_old_dump.sql\` as the source for the initial data migration script. The goal is to map the flat \`item\` table to the new FRBR hierarchy.
```

### 3\. Using the @ Symbol in VS Code

Most AI extensions (including Gemini and Copilot) support "Mentions." When you are chatting with Gemini in the VS Code sidebar, you can type:

> *"@file:legacy\_prototype.py How did I handle the ISBN lookup here? Re-implement this using the new Flask Blueprints structure."*

By explicitly mentioning the file, you force the AI to read that specific "old" code and apply it to the "new" context.

### 4\. Handling the SQL Dump (.gz file)

Since Gemini can't "read" a compressed `.gz` file directly in the editor, you should:

1. **Unzip it.**
2. **Keep the `.sql` file** in your `docs/context` folder.
3. **Add a `.gitignore` entry** for the large SQL file if you don't want it versioned on GitHub, but keep it in your local folder so Gemini can see it during development.

### 5\. Setting up "Context Instructions" (System Prompt)

If you are using the Gemini Code Assist, you can often go into the settings and define a **System Prompt**. You should paste this in:

> "You are the iqoqo coding sidekick. You have access to a research document (`docs/context/research.md`) and legacy code (`docs/context/legacy/`). When I ask to build a feature, check the research document for the FRBR requirements and the legacy code for existing logic before suggesting new code."

---

### Pro-Tip for Migration

Once you have the new PostgreSQL schema running, you can ask Gemini in VS Code:

> *"Look at `@file:schema_new.sql` and `@file:schema_old.sql`. Write a Python migration script that extracts books from the old 'item' table and creates corresponding 'Work', 'Expression', and 'Manifestation' entries in the new DB."*

**Does this setup make sense? If you're ready, I can help you write that specific `GEMINI.md` file right now so you can drop it into your new repo.**

can I put it in.gemini/context instead?

iqoqo coding sidekick

Custom Gem

Yes, you absolutely can. In fact, using a hidden directory like `.gemini/` is a cleaner, more professional way to manage project metadata without cluttering your root directory.

Most modern AI tools (including Gemini and various VS Code "Agentic" extensions) are designed to look into hidden configuration folders.

### The Setup

1. Create a folder named `.gemini/` at the root of your repo.
2. Inside, create a file named `instructions.md` (or `context.md`).
3. Place all the research context, logic rules, and legacy references there.

---

### The Content for.gemini/instructions.md

Copy and paste this directly. It is designed to "prime" the AI with the exact persona and technical requirements we've established:

Markdown

```markdown
# iqoqo Project Instructions & Context

## 🤖 Persona
You are the **iqoqo coding sidekick**. You are a senior full-stack architect and Semantic Web expert. You are building a "Library of Everything" that is distributed, federated, and user-owned.

## 🏛️ Core Architecture (FRBRoo)
Every object in this system MUST follow the Functional Requirements for Bibliographic Records (FRBR) hierarchy:
1. **Work:** The abstract concept (e.g., "The Hobbit").
2. **Expression:** The specific version (e.g., The English text, or an Audio Recording).
3. **Manifestation:** The physical/digital edition (e.g., 1937 Allen & Unwin Hardcover, ISBN: 9780048230706).
4. **Item:** The specific copy the user owns (e.g., "The copy on my shelf with the coffee stain").

## 🛠️ Tech Stack & Implementation
- **Backend:** Python 3.11+ / Flask.
- **Database:** PostgreSQL. Use \`JSONB\` for flexible metadata and PostgreSQL Full-Text Search.
- **Linked Data:** Use \`rdflib\` to expose every entity as JSON-LD/RDF.
- **API-First:** Design for Web UI, but ensure the API is robust enough for future iOS/Android apps.
- **Deployment:** The service must be fully containerized via Docker.

## 📂 Context & Legacy References
- **Research:** Refer to \`docs/context/feasibility_study.md\` for the original vision.
- **Legacy Code:** See \`docs/context/legacy_prototype.txt\`. 
    - Key logic to port: Barcode scanning, ISBN metadata fetching.
    - Key change: Move from the old "flat" item table to the 4-tier FRBR structure.
- **Migration:** Use the SQL schema in \`docs/context/legacy_db.sql\` to map existing book data into the new FRBR model.

## 📜 Coding Principles
- **No "Flat" Data:** Always ask "Is this a Work, Expression, or Manifestation?" before creating a table.
- **Content Negotiation:** Endpoints should support \`Accept: application/ld+json\`.
- **Privacy:** Design with a "local-first" mindset. Users choose what to sync to the central iqoqo discovery service.
```

---

### Why this works

By putting this in `.gemini/instructions.md`, every time you open a chat in VS Code and mention your project, the AI "boots up" with these constraints. It won't suggest a generic SQL table for "Books" because it knows it must follow the **FRBR** hierarchy.

### Next Step

Now that your repo and context are defined, would you like me to **design the PostgreSQL schema** that maps these four FRBR entities? This will be the "spine" of the entire project.

do you mean I don't have to keep GEMINI.md file - but I could move it.gemini/instructions.md?

iqoqo coding sidekick

Custom Gem

Exactly. You can move that logic into `.gemini/instructions.md`.

While `GEMINI.md` is a common pattern for "visibility" (so you can see it in your file explorer easily), moving it into the `.gemini/` folder is a cleaner "system" approach. It signals to the AI—and to other developers—that this is a **configuration** for the AI assistant rather than project documentation for humans.

### The Recommended Structure

Here is how your repository root should look to give Gemini in VS Code the best possible "brain":

Plaintext

```markdown
iqoqo/
├── .gemini/
│   └── instructions.md     <-- (The "Brain" / System Prompt)
├── docs/
│   └── context/
│       ├── feasibility_study.md
│       ├── legacy_prototype.txt
│       └── legacy_db.sql
├── app/                    <-- (New Flask Code)
├── docker-compose.yml
└── .gitignore
```

### Why.gemini/instructions.md is better

1. **Cleaner Root:** Your project root stays focused on code (`app/`, `tests/`, `docker-compose.yml`).
2. **Context Isolation:** You can add other files to `.gemini/` later, like `style-guide.md` or `api-spec.md`, allowing you to modularize the instructions you give the AI.
3. **Automatic Loading:** Gemini is designed to look for instructions in hidden config folders.

---

### One Final "Migration" Tip for your Context Files

When you move your legacy files into `docs/context/`, I recommend adding a small header at the top of each file (even the SQL one) to tell Gemini what it's looking at.

For example, at the top of `legacy_db.sql`:

SQL

```markdown
-- CONTEXT: This is the legacy PostgreSQL schema from the first iqoqo prototype.
-- Mapping Goal: The 'item' table here is "flat." It must be mapped to 
-- Work/Expression/Manifestation in the new version.
```

---

### Ready to build the "Spine"?

Now that we have the "brain" (instructions) and the "memory" (context files) sorted out, would you like me to generate the **SQL Schema for the new FRBR-based database**?

This schema will define exactly how **Works**, **Expressions**, **Manifestations**, and **Items** are linked in PostgreSQL. Shall we start there?

ok, write up a directory structure will ALL files that need to be created in the project to realize our goals

iqoqo coding sidekick

Custom Gem

Here is the comprehensive directory structure and file list required to realize the **iqoqo** vision. This structure separates the **Semantic/FRBR logic** from the **Web/API layer**, ensuring the system is modular and ready for federation.

I have annotated each file so you know *exactly* why it exists.

### 📂 Project Root iqoqo/

This is your high-level workspace.

Plaintext

```markdown
iqoqo/
├── .gemini/
│   └── instructions.md       # The "Brain" for your AI assistant (as discussed).
├── .env                      # Secrets (DB passwords, API keys) - NEVER commit this.
├── .env.example              # Template for .env (safe to commit).
├── .gitignore                # Standard Python/Docker gitignore.
├── README.md                 # Project vision, setup guide, and badge links.
├── requirements.txt          # Python deps: Flask, RDFLib, psycopg2-binary, requests.
├── docker-compose.yml        # Orchestrates Flask app + PostgreSQL db.
└── run.py                    # Entry point to start the Flask dev server.
```

---

### 📂 App Core app/

This is where the actual code lives. We use the **Application Factory** pattern to handle the complexity of database connections and multiple blueprints (API vs. Web UI).

Plaintext

```markdown
app/
├── __init__.py               # Flask app factory. Initializes DB, registers Blueprints.
├── config.py                 # Configuration classes (DevelopmentConfig, ProductionConfig).
│
├── core/                     # 🧠 THE BRAIN: Pure Python logic (No HTTP code here).
│   ├── __init__.py
│   ├── frbr.py               # Defines the FRBR entities (Work, Expression, Manifestation).
│   ├── catalog.py            # Logic to search/add items to the DB.
│   ├── scanner.py            # Logic to handle barcode/ISBN lookups (external APIs).
│   └── rdf_serializer.py     # Converts DB objects into JSON-LD/Turtle for Linked Data.
│
├── db/                       # 🗄️ DATABASE: PostgreSQL handling.
│   ├── __init__.py
│   ├── schema.sql            # The MASTER Schema (FRBR-based tables).
│   └── connector.py          # Helper functions to get DB connection/cursor.
│
├── api/                      # 🔌 API: JSON endpoints for Federation/Mobile Apps.
│   ├── __init__.py
│   ├── catalog_api.py        # GET/POST /api/items (Search & Add).
│   └── federation_api.py     # GET /api/rdf (Expose Linked Data to other nodes).
│
└── web/                      # 🖥️ UI: The Browser Interface (HTMX/Jinja2).
    ├── __init__.py
    ├── routes.py             # Render HTML templates.
    ├── static/
    │   ├── css/
    │   │   └── style.css     # Clean, minimal CSS.
    │   └── js/
    │       └── scanner.js    # Client-side barcode processing (QuaggaJS or similar).
    └── templates/
        ├── base.html         # Main layout (Nav, Footer).
        ├── index.html        # Search bar and recent items.
        ├── item.html         # Detailed view of a Work/Manifestation.
        └── scan.html         # Camera interface for adding items.
```

---

### 📂 Context & Migration docs/ & scripts/

These folders bridge the gap between your old prototype and the new system.

Plaintext

```markdown
docs/
├── context/
│   ├── feasibility_study.md  # Your converted research doc.
│   ├── legacy_db.sql         # The old 'item' table dump.
│   └── legacy_logic.txt      # Old Python code snippets (reference).
└── ontology/
    └── iqoqo.ttl             # Your custom RDF vocabulary extensions (if any).

scripts/
├── setup_db.py               # Runs 'app/db/schema.sql' to init the fresh DB.
└── migrate_legacy.py         # ⚠️ CRITICAL: Script to read 'legacy_db.sql' 
                              # and split "Books" into Work->Expression->Manifestation.
```

---

### 📂 Deployment deploy/

Everything needed to ship this as a "self-hosted" service.

Plaintext

```markdown
deploy/
├── Dockerfile                # Python environment setup.
├── nginx.conf                # (Optional) Reverse proxy config if needed later.
└── wait-for-postgres.sh      # Utility script to ensure DB is up before App starts.
```

---

### 📝 Immediate To-Do List

To get this structure into reality, here is your checklist:

1. **Create the Folders:** Run `mkdir -p app/{core,db,api,web/templates,web/static} docs/{context,ontology} scripts deploy .gemini`
2. **Create `.gemini/instructions.md`:** Paste the system prompt we generated earlier.
3. **Create `app/db/schema.sql`:** This is the most critical file. We need to define the 4-tier FRBR tables here.
4. **Create `requirements.txt`:**

Plaintext

```markdown
Flask==3.0.*
psycopg2-binary==2.9.*
rdflib==7.*
requests==2.*
python-dotenv
gunicorn
```

1. **Create `docker-compose.yml`:** A simple definition for `web` (Flask) and `db` (Postgres 16).

**Shall I write the content for `app/db/schema.sql` (The FRBR Database Schema) next?** This is the foundation upon which everything else rests.

I want to use alchemy models instead of app/db/schema.sql, and I put all docs/context into.gemini/context, but it's a good idea to keep ontologies in docs/ontology - please update your structures

iqoqo coding sidekick

Custom Gem

This is a great decision. Using **SQLAlchemy ORM** instead of raw SQL makes the code much more maintainable, easier to migrate, and significantly simpler to query using Python syntax. It also handles the complex joins required by the FRBR hierarchy much more gracefully.

Here is the **updated project structure** reflecting the move to SQLAlchemy and the new context location.

### 📂 Updated Project Root iqoqo/

Plaintext

```markdown
iqoqo/
├── .gemini/
│   ├── instructions.md       # The "Brain" (System Prompt).
│   └── context/              # 📂 MOVED: Reference docs & legacy code here.
│       ├── feasibility_study.md
│       ├── legacy_prototype.txt
│       └── legacy_db.sql
├── .env                      # Secrets (DB connection string).
├── .gitignore
├── README.md
├── requirements.txt          # Added: flask-sqlalchemy, flask-migrate
├── docker-compose.yml
└── run.py
```

### 📂 App Core app/ (Refined for SQLAlchemy)

Plaintext

```markdown
app/
├── __init__.py               # Flask App Factory (Initializes SQLAlchemy).
├── config.py                 # Config settings.
│
├── core/                     # 🧠 Business Logic.
│   ├── __init__.py
│   ├── frbr_service.py       # Logic to orchestrate Work/Exp/Man/Item creation.
│   └── ingest.py             # Logic for parsing ISBN metadata into models.
│
├── db/                       # 🗄️ Database Layer (ORM).
│   ├── __init__.py           # Exposes 'db' object.
│   └── models.py             # 🌟 NEW: The Python classes defining FRBR tables.
│
├── api/                      # 🔌 REST API.
│   ├── __init__.py
│   └── routes.py             # Endpoints using models (e.g., Item.query.all()).
│
└── web/                      # 🖥️ User Interface.
    ├── __init__.py
    ├── routes.py
    └── templates/            # Jinja2 HTML templates.
```

### 📂 Documentation & Scripts

Plaintext

```markdown
docs/
└── ontology/                 # 📂 KEPT: Your Semantic Definitions.
    └── iqoqo.ttl             # Custom Turtle file for extensions.

scripts/
└── migrate_legacy.py         # Script to load data from .gemini/context/legacy_db.sql
                              # and insert into the new SQLAlchemy models.
```

---

### 🌟 The Key File: app/db/models.py

Since this is the most critical part of your new architecture, here is the boilerplate code to get the **FRBR** hierarchy working with **SQLAlchemy** and **PostgreSQL JSONB**.

You can drop this directly into `app/db/models.py`:

Python

```markdown
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

# Initialize the db object here or in __init__.py to avoid circular imports
db = SQLAlchemy()

class Work(db.Model):
    """
    FRBR Group 1: Work
    A distinct intellectual or artistic creation.
    e.g., "The Hobbit" (the story itself, regardless of language).
    """
    __tablename__ = 'works'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    # Flexible metadata (e.g., original_language, first_performance_date)
    meta = db.Column(JSONB, default={})
    
    # Relationships
    expressions = db.relationship('Expression', backref='work', lazy=True)

class Expression(db.Model):
    """
    FRBR Group 1: Expression
    The intellectual realization of a work.
    e.g., The English text of The Hobbit, or the German translation.
    """
    __tablename__ = 'expressions'
    id = db.Column(db.Integer, primary_key=True)
    work_id = db.Column(db.Integer, db.ForeignKey('works.id'), nullable=False)
    content_type = db.Column(db.String(50)) # e.g., 'text', 'sound', 'notated_music'
    language = db.Column(db.String(10))     # e.g., 'en', 'pl'
    meta = db.Column(JSONB, default={})
    
    # Relationships
    manifestations = db.relationship('Manifestation', backref='expression', lazy=True)

class Manifestation(db.Model):
    """
    FRBR Group 1: Manifestation
    The physical or digital embodiment of an expression.
    e.g., The 1937 Allen & Unwin Hardcover edition.
    """
    __tablename__ = 'manifestations'
    id = db.Column(db.Integer, primary_key=True)
    expression_id = db.Column(db.Integer, db.ForeignKey('expressions.id'), nullable=False)
    
    # Identifiers
    isbn13 = db.Column(db.String(13), index=True, unique=True)
    upc = db.Column(db.String(12), index=True)
    ean = db.Column(db.String(13), index=True)
    
    publisher = db.Column(db.String(255))
    publication_date = db.Column(db.Date)
    meta = db.Column(JSONB, default={}) # Stores cover images, page count, dimensions
    
    # Relationships
    items = db.relationship('Item', backref='manifestation', lazy=True)

class Item(db.Model):
    """
    FRBR Group 1: Item
    A single exemplar of a manifestation.
    e.g., The specific book on your shelf.
    """
    __tablename__ = 'items'
    id = db.Column(db.Integer, primary_key=True)
    manifestation_id = db.Column(db.Integer, db.ForeignKey('manifestations.id'), nullable=False)
    
    # User ownership data
    owner_id = db.Column(db.String(100)) # Could link to a User table later
    status = db.Column(db.String(50), default='available') # available, lent, lost, wish_list
    condition = db.Column(db.String(50))
    
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    meta = db.Column(JSONB, default={}) # Custom tags, notes, location on shelf
```

### Next Step 2

This structure is ready to go. When you initialize this with Flask-Migrate, it will automatically generate the PostgreSQL tables.

**Shall I give you the content for `docker-compose.yml` next, so you can spin up the Database and the App in one command?**

# Contributing to iqoqo

Thank you for your interest in contributing to **iqoqo**! This guide will help you get started with the development process, coding standards, and contribution workflow.

## 🎯 Project Philosophy

iqoqo is built on these core principles:

1. **FRBR-First Architecture**: Every entity follows the Work → Expression → Manifestation → Item hierarchy
2. **Privacy & Data Sovereignty**: Users control their data; federation is opt-in
3. **Semantic Web Standards**: All entities are addressable URIs with RDF/JSON-LD representations
4. **API-First Design**: The API is the primary interface; UIs are consumers
5. **Local-First**: The system works offline; sync is a feature, not a requirement

## 🚀 Getting Started

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR-USERNAME/iqoqo.git
cd iqoqo
git remote add upstream https://github.com/sebastiankruk/iqoqo.git
```

### 2. Set Up Development Environment

Follow the complete setup instructions in [INSTALL.md](INSTALL.md):

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
npm install

# Initialize database (first time only)
docker compose up -d db
.venv/bin/python scripts/init_db.py --seed-file data/seed_example.json
```

### 3. Start/Stop Development Environment

**Start everything (Colima, PostgreSQL, Flask):**

```bash
make start
```

This will:

1. Start Colima (Docker runtime for macOS)
2. Start PostgreSQL database container
3. Activate virtual environment
4. Run Flask development server at [http://localhost:5000](http://localhost:5000)

**Stop everything cleanly:**

```bash
make stop
```

This will:

1. Stop Flask server
2. Stop database container
3. Keep Colima running (stops only if you run `colima stop`)

**Verify it's working:**

```bash
# Check API endpoint
curl http://localhost:5000/api/stats

# Access web interface
open http://localhost:5000
```

### 4. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

## 📋 Development Workflow

### Before You Code

1. **Check existing issues** - See if your feature/bug is already being worked on
2. **Open an issue** - Discuss your proposed changes before implementing
3. **Read the architecture docs**:
   - **[ARCHITECTURE.md](ARCHITECTURE.md)** - Complete FRBR hierarchy guide with examples
   - [docs/ontology/iqoqo.ttl](ontology/iqoqo.ttl) - Formal ontology specification

### While You Code

#### Code Quality Standards

All code must pass quality checks before being merged. Run these before committing:

```bash
# Check everything
make lint

# Auto-fix formatting
make format

# Run tests
make test
```

#### Python Standards

- **Formatting**: Black with 120-character line length
- **Linting**: Ruff (replaces flake8, pylint, isort checks)
- **Type Hints**: Use type annotations; checked by mypy
- **Imports**: Organized by isort (standard → third-party → local)

```python
# Good example
from typing import Optional

from flask import Blueprint, jsonify
from sqlalchemy.orm import Session

from app.db.models import Work, Expression, Manifestation, Item


def get_or_create_work(session: Session, title: str, author: str) -> Work:
    """Get existing Work or create new one following FRBR model."""
    work = session.query(Work).filter_by(title=title, author=author).first()
    if not work:
        work = Work(title=title, author=author)
        session.add(work)
        session.commit()
    return work
```

#### JavaScript Standards

- **Formatting**: Prettier
- **Linting**: ESLint with recommended rules
- **Style**: Modern ES6+ features encouraged

```javascript
// Good example
const scanBarcode = async (isbn) => {
    try {
        const response = await fetch(`/api/isbn/${isbn}`);
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Barcode scan failed:', error);
        showToast('error', 'Failed to scan barcode');
    }
};
```

#### CSS Standards

- **Formatting**: Prettier
- **Linting**: stylelint with standard config
- **Approach**: Use Bootstrap classes first; custom CSS as needed

### Development Commands Quick Reference

```bash
# Start/Stop
make start          # Start Colima, PostgreSQL, and Flask server
make stop           # Stop Flask and database (keeps Colima running)

# Code Quality
make lint           # Run all linting checks (Python, JS, CSS, Markdown)
make format         # Auto-format all code
make test           # Run all tests (includes linting)

# Database
make db-init        # Initialize database with seed data
make db-seed        # Load seed data into existing database
make db-export      # Export database to data/backup.json
make db-stats       # Show database statistics

# Python Environment
source .venv/bin/activate  # Activate virtual environment
.venv/bin/python           # Use venv Python directly
.venv/bin/pytest           # Run tests with venv
```

**Pro tip**: Use `make help` to see all available commands.

### Writing Tests

All new features require tests. We use pytest with Flask's test client.

**Note**: Running `pytest` automatically includes linting checks (ruff, mypy, black, isort). The test suite ensures code quality by failing if any linting issues are detected.

```python
# tests/test_api.py
def test_isbn_lookup_success(client):
    """Test successful ISBN metadata lookup."""
    response = client.get('/api/isbn/9780048230706')
    assert response.status_code == 200
    data = response.get_json()
    assert 'title' in data
    assert 'authors' in data
```

Run tests:

```bash
pytest                    # Run all tests (includes linting checks)
pytest tests/test_api.py  # Run specific test file
pytest -v                 # Verbose output
pytest -k "isbn"          # Run tests matching "isbn"
pytest tests/test_linting.py  # Run only linting checks
```

### Database Changes

For schema changes:

```bash
# Create migration
flask db migrate -m "Description of change"

# Review the generated migration in migrations/versions/
# Edit if necessary

# Apply migration
flask db upgrade
```

**Important**: Always follow FRBR principles:

- Don't create "flat" tables mixing Work/Expression/Manifestation concerns
- Use proper foreign keys to link FRBR entities
- Add JSONB columns for flexible metadata, not endless varchar columns

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```text
feat: add barcode scanning for board games
fix: resolve ISBN lookup timeout issue
docs: update FRBR model diagram
test: add coverage for manifestation API
refactor: extract ISBN service to separate module
```

## 🔄 Pull Request Process

### 1. Ensure Quality

```bash
# These must all pass
make lint
make test
```

### 2. Update Documentation

- Update README.md if adding user-facing features
- Add docstrings to new functions/classes
- Update API documentation for new endpoints
- Add comments explaining non-obvious FRBR modeling decisions

### 3. Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then open a PR on GitHub with:

- **Clear title** following conventional commits format
- **Description** explaining what and why (not how - that's in the code)
- **Testing notes** - how to test the changes
- **Screenshots** for UI changes
- **Related issues** - Reference with "Fixes #123"

### 4. Code Review

- Address reviewer feedback promptly
- Don't take feedback personally - it's about the code, not you
- Be open to suggestions for better FRBR modeling
- Ask questions if review comments are unclear

### 5. Merge

Once approved:

- Squash commits if requested
- Ensure CI passes (GitHub Actions will run all quality checks)
- A maintainer will merge your PR

## 🏗️ Architecture Guidelines

### FRBR Modeling Rules

When adding features, always ask:

1. **Is this a Work?** - The abstract creative content
   - Example: "The Hobbit" as a concept
   - Has: title, creators, subject

2. **Is this an Expression?** - A specific realization
   - Example: "The Hobbit in English" vs "Le Hobbit en français"
   - Has: language, form (text, audio, etc.)

3. **Is this a Manifestation?** - A published edition
   - Example: "1937 Allen & Unwin hardcover, ISBN 9780048230706"
   - Has: publisher, ISBN, format, cover image

4. **Is this an Item?** - A specific copy
   - Example: "My personal copy with coffee stain on page 42"
   - Has: condition, location, acquisition date, notes

### API Design Principles

- **RESTful**: Use proper HTTP methods (GET/POST/PUT/DELETE)
- **JSON-LD**: Support `Accept: application/ld+json` for Linked Data
- **Versioning**: Prefix with `/api/v1/` for future compatibility
- **Errors**: Return meaningful error messages with proper HTTP status codes
- **Pagination**: Use `?page=1&per_page=20` for list endpoints
- **Filtering**: Support `?author=tolkien&year=1937` style filters

### Database Guidelines

- **Use SQLAlchemy ORM**: Don't write raw SQL unless absolutely necessary
- **Type JSONB metadata carefully**: Document expected structure in model docstrings
- **Add indexes**: For foreign keys and frequently queried columns
- **Migration safety**: Test `upgrade` and `downgrade` paths

## 🐛 Reporting Issues

### Bug Reports

Include:

- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment (OS, Python version, Docker version)
- Relevant logs (from `flask run` or `docker compose logs`)

### Feature Requests

Include:

- Use case - what problem does this solve?
- How it fits the FRBR model
- Whether it affects privacy/federation concerns
- Examples from other library systems (if applicable)

## 📚 Additional Resources

- [FRBR Overview](https://www.ifla.org/publications/functional-requirements-for-bibliographic-records/)
- [FRBRoo Documentation](https://www.cidoc-crm.org/frbroo/)
- [JSON-LD Specification](https://json-ld.org/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)

## 💬 Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: Open a GitHub Issue
- **Chat**: Join our community (coming soon)

## 📄 Code of Conduct

Be respectful, inclusive, and constructive. We're building a library for everyone.

---

**Thank you for contributing to iqoqo!** Every contribution, no matter how small, helps build the Library of Everything. 📚✨

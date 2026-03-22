---
trigger: always_on
---

---
description: "Global coding standards and architectural rules for the iqoqo project."
---
# iqoqo Global Project Rules

## 1. General Architectural Principles

- **Domain First:** This is a "Library of Everything" built on the FRBR (Functional Requirements for Bibliographic Records) ontology. Always respect the Work -> Expression -> Manifestation -> Item hierarchy.
- **Linked Open Data:** Ensure all metadata is exposed or capable of being exposed as RDF/JSON-LD.
- **Do Not Hallucinate Metadata:** If an external service (e.g., ISBN lookup) fails, fail gracefully. Do not generate fake book covers or ISBNs.

## 2. Python Backend (Flask)

- **Typing:** Use strict Python type hints (`typing` module) for all function signatures and return types.
- **ORM:** Use SQLAlchemy 2.0 style syntax (e.g., `select()`, `session.execute()`). Avoid legacy `Query` usage.
- **Linting:** Code must pass `pylint` and `flake8` without warnings. Use `# noqa` only when absolutely necessary and add a comment explaining why.
- **API Responses:** All API responses must be JSON. Use consistent error formatting: `{"error": "description", "code": 400}`.

## 3. Frontend (Next.js / TypeScript)

- **Framework:** Use Next.js App Router (`app/` directory). Do not use the legacy `pages/` router.
- **Components:** Write functional components using React hooks. Do not use class components.
- **Styling:** Use Tailwind CSS exclusively. Use Shadcn UI for standard components (found in `components/ui/`). Do not write raw CSS unless necessary.
- **State Management:** Keep state as local as possible. Prefer Server Components where interactivity is not required.

## 4. Git & Pull Requests

- **Commits:** Strictly use Conventional Commits (e.g., `feat:`, `fix:`, `chore:`, `docs:`).
- **PR Finalization:** All code pushed to a `release/*` branch must be accompanied by updated documentation in `docs/CHANGELOG.md` and pass `make lint` and `make test`.

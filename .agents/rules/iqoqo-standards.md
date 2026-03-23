---
trigger: always_on
---

---
description: "Global coding standards and architectural rules for the iqoqo project."
---
# iqoqo Global Project Rules

## Decision Making & Feature Preservation

- **Plan Over Comments:** The project plan files in `.github/context/private-notes/` are the absolute source of truth. Never blindly delete UI components, filters, or API parameters just because a PR review comment says they are "unused" or "unsupported". If the feature is planned, fix the implementation (e.g., pass the missing parameter to the backend) instead of removing the code.

## General Architectural Principles

- **Domain First:** This is a "Library of Everything" built on the FRBR (Functional Requirements for Bibliographic Records) ontology. Always respect the Work -> Expression -> Manifestation -> Item hierarchy.
- **Linked Open Data:** Ensure all metadata is exposed or capable of being exposed as RDF/JSON-LD.
- **Do Not Hallucinate Metadata:** If an external service (e.g., ISBN lookup) fails, fail gracefully. Do not generate fake book covers or ISBNs.

## Python Backend (Flask)

- **Typing:** Use strict Python type hints (`typing` module) for all function signatures and return types.
- **ORM:** Use SQLAlchemy 2.0 style syntax (e.g., `select()`, `session.execute()`). Avoid legacy `Query` usage.
- **Linting:** Code must pass `pylint` and `flake8` without warnings. Use `# noqa` only when absolutely necessary and add a comment explaining why.
- **Pylint & SQLAlchemy:** `pylint` falsely flags SQLAlchemy's `func.count` as not callable (`E1102`). Whenever you write `func.count()`, immediately append `# pylint: disable=not-callable` to the line to prevent CI failures.
- **API Responses:** All API responses must be JSON. Use consistent error formatting: `{"error": "description", "code": 400}`.
- **Aggregates:** Prefer `GROUP BY` aggregate queries over dictionary comprehensions that execute N+1 `COUNT` queries.

## Frontend (Next.js / TypeScript)

- **Framework:** Use Next.js App Router (`app/` directory). Do not use the legacy `pages/` router.
- **Components:** Write functional components using React hooks. Do not use class components.
- **Styling:** Use Tailwind CSS exclusively. Use Shadcn UI for standard components (found in `components/ui/`). Do not write raw CSS unless necessary.
- **State Management:** Keep state as local as possible. Prefer Server Components where interactivity is not required.

## Documentation & Markdown

- **MarkdownLint:** Use ATX-style headings (`# Heading`) exclusively. Do not use Setext-style (`===` or `---` underlines).
- **Code Blocks:** When writing shell commands in Markdown, explicitly tag them as `bash` or `sh`. Do not tag them as `markdown`.

## Git & Pull Requests

- **Commits:** Strictly use Conventional Commits (e.g., `feat:`, `fix:`, `chore:`, `docs:`).
- **PR Finalization:** All code pushed to a `release/*` branch must be accompanied by updated documentation in `docs/CHANGELOG.md` and pass `make lint` and `make test`.

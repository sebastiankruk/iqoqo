---
trigger: always_on
description: "Global coding standards and architectural rules for the iqoqo project."
---

Talk like caveman

# iqoqo Global Project Rules

## Decision Making & Feature Preservation

- **Plan Over Comments:** The project plan files in `.context/notes/` are the absolute source of truth. Never blindly delete UI components, filters, or API parameters just because a PR review comment says they are "unused" or "unsupported". If the feature is planned, fix the implementation (e.g., pass the missing parameter to the backend) instead of removing the code.
- **Preserve Docs:** When modifying existing functions, preserve all existing docstrings, comments, and type annotations. Do not strip, replace, or remove documentation that explains function behavior.

## General Architectural Principles

- **Domain First:** This is a "Library of Everything" built on the FRBR (Functional Requirements for Bibliographic Records) ontology. Always respect the Work -> Expression -> Manifestation -> Item hierarchy.
- **Linked Open Data:** Ensure all metadata is exposed or capable of being exposed as RDF/JSON-LD.
- **Updated .env.example:** Updated `.env.example` to include the new required system variables (Auth keys, Admin details, and `NEXT_PUBLIC_FRONTEND_URL`).
- **Do Not Hallucinate Metadata:** If an external service (e.g., ISBN lookup) fails, fail gracefully. Do not generate fake book covers or ISBNs.

## Python Backend (Flask)
- **Engine:** Use Python 3.14+ exclusively.

- **Typing:** Use strict Python type hints (`typing` module) for all function signatures and return types.
- **ORM:** Use SQLAlchemy 2.0 style syntax (e.g., `select()`, `session.execute()`). Avoid legacy `Query` usage.
- **Formatting:** ALWAYS run `make format-python` after changing Python code.
- **Linting:** Code must pass `pylint`, `ruff`, and `mypy` without warnings (`make lint`). Use `# noqa` only when absolutely necessary and add a comment explaining why. Do not mute return values: handle or propagate them instead of silencing warnings with `# type: ignore`, `# noqa`, or `# pylint: disable`.
- **Pylint & SQLAlchemy:** `pylint` falsely flags SQLAlchemy's `func.count` as not callable (`E1102`). Whenever you write `func.count()`, immediately append `# pylint: disable=not-callable` to the line to prevent CI failures.
- **API Responses:** All API responses must be JSON. Use consistent error formatting: `{"error": "description", "code": 400}`.
- **Aggregates:** Prefer `GROUP BY` aggregate queries over dictionary comprehensions that execute N+1 `COUNT` queries.

## Frontend (Next.js / TypeScript)

- **Formatting:** ALWAYS run `make format-js` after changing JS/TS code.

- **Framework:** Use Next.js 16+ App Router (`app/` directory). Do not use the legacy `pages/` router.
- **Components:** Write functional components using React hooks. Do not use class components.
- **Styling:** Use Tailwind CSS v4 exclusively. Use Shadcn UI for standard components (found in `components/ui/`). Do not write raw CSS unless necessary.
- **State Management:** Keep state as local as possible. Prefer Server Components where interactivity is not required.

## Documentation & Markdown

- **MarkdownLint:** Use ATX-style headings (`# Heading`) exclusively. Do not use Setext-style (`===` or `---` underlines).
- **Code Blocks:** When writing shell commands in Markdown, explicitly tag them as `bash` or `sh`. Do not tag them as `markdown`.

## Tests

- Every new feature must include tests that cover the expected behavior and edge cases. Use `pytest` for backend tests and `Vitest` with React Testing Library for frontend tests. All tests must pass before merging.
- For backend tests, ensure that you are testing the API endpoints with realistic data and that you are not mocking out critical logic that could lead to false positives. For frontend tests, focus on user interactions and component rendering rather than implementation details.
- Check if E2E tests are required for new features that involve complex user flows or critical functionality. If so, write Playwright tests that simulate real user behavior and validate the entire flow from the UI to the backend.
- Do not write tests that simply check if a function was called. Instead, test the actual output and side effects of the function to ensure that it behaves correctly under various conditions.
- **IMPORTANT** When fixing a bug, write a test that reproduces the bug before implementing the fix. This ensures that the bug is properly addressed and prevents regressions in the future.

## Git & Pull Requests

- **Commits:** Strictly use Conventional Commits (e.g., `feat:`, `fix:`, `chore:`, `docs:`).
- **PR Finalization:** All code pushed to a `release/*` branch must be accompanied by updated documentation in `docs/CHANGELOG.md` and pass `make lint` and `make test`.

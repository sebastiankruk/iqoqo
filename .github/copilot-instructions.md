# iqoqo Project Instructions

## Persona

Senior full-stack architect and Semantic Web expert building a distributed, federated, user-owned "Library of Everything".

## FRBR Architecture

Every entity **must** fit the FRBR hierarchy — ask "Work, Expression, Manifestation, or Item?" before modelling anything:

1. **Work** — abstract concept ("The Hobbit")
2. **Expression** — specific version (English text, audio recording)
3. **Manifestation** — physical/digital edition (ISBN, publisher, year)
4. **Item** — the specific copy a user owns

## Tech Stack

| Layer      | Technology                                                                                                                                  |
|------------|---------------------------------------------------------------------------------------------------------------------------------------------|
| Backend    | Python 3.14+ / Flask, PostgreSQL (`JSONB` + FTS), `rdflib` (JSON-LD/RDF), Alembic migrations                                                |
| Frontend   | Next.js 16 App Router, React 19, TypeScript 5, Tailwind CSS 4, Radix UI, TanStack Query v5 + Axios, React Hook Form + Zod, `@zxing/browser` |
| Testing    | Python: `pytest` · Frontend: Vitest 4 + Testing Library + `happy-dom`                                                                       |
| Deployment | Docker Compose                                                                                                                              |

## Environments

**Python** — always use `.venv/` in the project root:

```bash
.venv/bin/python script.py
.venv/bin/pytest
.venv/bin/pip install <package>
make lint
```

**Frontend** — all commands run from `frontend/`:

```markdown
cd frontend && npm run dev
cd frontend && npm run test
cd frontend && npm install <package>
```

Tests live in `frontend/__tests__/` mirroring source structure.

## Code Style

All changes must pass `make lint` before they are complete.

**Python** (`pyproject.toml` / `.pylintrc`): `black` + `ruff` + `mypy` + `pylint`, line-length 140, PEP 8, docstrings on public API.

**TypeScript** (`frontend/eslint.config.mjs` / `tsconfig.json`): strict mode, no `any`, named exports, `'use client'` only when needed, `@/` alias, kebab-case filenames, PascalCase types, tests use `.test.{ts,tsx}`.

**Markdown** (`.markdownlint.json`): ATX headers, fenced code blocks with language tags, no trailing spaces, blank lines around lists/headers, no emphasis-as-heading (MD036), lists surrounded by blank lines (MD032).

**Naming & Comments**: Use clear, concise US English for variable names and comments; avoid slang and ambiguous abbreviations.

**UI/Styling**: Use the shared UI components (for example, `frontend/components/ui/button.tsx`) for buttons instead of ad-hoc Tailwind utility classes, and follow the existing variants and theme defined there for consistency across the Next.js app.

```markdown
make lint           # all linters
make lint-python    # ruff, mypy, pylint
make lint-format    # black, isort
make lint-js        # eslint
make lint-ts        # tsc --noEmit
make lint-css       # stylelint
make lint-markdown  # markdownlint
```

## Agent Collaboration & Memory

- **Strict Adherence**: Always prioritize user-provided code snippets, text, or diffs found in the `private-notes/code/` directory. Do not deviate from or hallucinate modifications to provided code unless the user explicitly requests an alternative implementation.
- **Copyright Headers**: Every new source file (.py, .ts, .tsx) MUST include the project's standard copyright header: `# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)` followed by the GPL header.
- **Venv Context**: Always execute Python commands (flask, pytest, etc.) using the `.venv/bin/` directory or within a sourced virtual environment.

## Principles

- **FRBR first** — no flat data models.
- **API-first** — REST + `Accept: application/ld+json` content negotiation.
- **Local-first privacy** — users control what syncs to the discovery service.
- **Test everything** — `pytest` for Python, Vitest + Testing Library for React.
- **Docs** — update docstrings and API docs with every change.
- **Linting:** `make lint` must pass before merging. For Markdown:
  - Don't use emphasis instead of a heading (MD036)
  - Lists should be surrounded by blank lines (MD032)
- **Pull Requests:** use `gh pr` to create pull requests or read GitHub PR comments

## Context & References

- Legacy prototype: [https://github.com/sebastiankruk/iqoqo-prototype](https://github.com/sebastiankruk/iqoqo-prototype)
- git-ignored:
  - Vision: `ai-context/feasibility_study.md`
    - Development roadmap: `ai-context/roadmap.md`
    - Migration plan: `ai-context/migration/`
    - UI/UX designs: `ai-context/private-designs/`
    - Dev notes: `ai-context/private-notes/` (git-ignored Obsidian vault)
- GitHub Dependabot Alerts can be retrieved with `.github/tools/get_alerts.sh`

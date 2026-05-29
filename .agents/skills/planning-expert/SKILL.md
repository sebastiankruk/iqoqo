---
name: planning-expert
description: "Skill for converting product improvement descriptions into implementation-ready plans with code snippets."
license: AGPL
compatibility:
  - opencode
metadata:
  audience: developers
---

# Skill: Planning Expert

This skill converts high-level product improvement descriptions into implementation-ready plans with code snippets, following existing codebase patterns.

## Tech Stack Context

- **Backend**: Python Flask, PostgreSQL, Pytest, Ruff/Black, Alembic, FRBR-based ontology mapping.
- **Frontend**: React, Next.js, TypeScript, Vitest, ESLint.
- **Orchestration**: `make lint`, `make test`.

## Input Format

The skill accepts product improvement descriptions from:

- `.context/notes/plan/` folder
- Direct prompts describing features with UI/UX objectives

## Core Directives

1. **Explore Before Planning**: Always explore relevant code paths first to understand existing patterns:
   - Backend API routes: `app/api/*.py`
   - Backend services: `app/core/*.py`
   - Frontend components: `frontend/components/**/*`
   - Database models: `app/db/models.py`, `app/db/core.py`

2. **Pattern Matching**: Match the style, conventions, and patterns found in the existing codebase:
   - Use existing function signatures as templates
   - Match import patterns
   - Use existing helper functions and utilities

3. **Output Incremental Snippets**: Output code that represents _additions_ or _patches_ to existing files:
   - Not full-file replacements (unless explicitly needed)
   - Use clear section markers: `# Add to app/api/admin.py after get_roles():`
   - Include context lines for the edit tool to locate insertion points

4. **Follow Implementation Expert Format**: Output format must be consumable by implementation_expert:
   - Clear file paths with "Add to {path}:" markers
   - Snippets wrapped in code fences with language tags
   - Brief description of what the code does

## Planning Workflow

1. **Parse Input**: Read the product improvement description from the source document.
2. **Explore Codebase**: Search for relevant existing code patterns:
   - Similar API routes in `app/api/`
   - Similar React components in `frontend/components/`
   - Database models in `app/db/`
3. **Draft Snippets**: Create incremental code based on exploration:
   - Backend: API routes, service functions, model updates
   - Frontend: React components, API client hooks
   - Database: Alembic migrations if needed
4. **Format Output**: Present the implementation plan with clear markers
5. **Save Plan**: Output the complete plan - user will move it to `plan/done/`

## Output Format Example

````markdown
## Implementation Plan: FRBR Content Editor

### Backend: Add FRBR Entity Update Endpoints

Add to `app/api/admin.py` after `update_user()`:

```python
@admin_bp.route("/frbr/<entity_type>/<int:entity_id>", methods=["PUT"])
@admin_required
def update_frbr_entity(entity_type, entity_id):
    """Update a FRBR entity (Work, Expression, Manifestation)."""
    # ... implementation
```
````

### Frontend: Add FRBR Editor Component

Add to `frontend/components/admin/frbr-editor.tsx`:

```tsx
export function FRBREditor({ entity }: { entity: FRBREntity }) {
  // ... implementation
}
```

## File Locations Reference

- Admin API: `app/api/admin.py`
- FRBR Service: `app/core/frbr_service.py`
- DB Models: `app/db/models.py`, `app/db/core.py`
- Frontend Admin: `frontend/components/admin/*.tsx`
- Frontend API client: `frontend/lib/api/*.ts`

Base directory for this skill: `.agents/skills/planning-expert`

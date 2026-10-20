## Context

Adapts Phase 6 admin UI components with shadcn AlertDialog and TanStack Query keys.

## Goals / Non-Goals

**Goals:**
- Ergonomic admin controls with real-time health indicators.

**Non-Goals:**
- End-user social feeds in admin interface.

## Decisions

### Shadcn UI Standards
* **Decision**: Use shadcn Dialog/AlertDialog and toast notifications per v0.8.1 C13 guidelines.
* **Rationale**: Maintain UI consistency.

## Risks / Trade-offs

- ('[Risk] Translation desynchronization', 'Mitigation: Add Vitest key parity test in `federation-i18n.test.ts`.')

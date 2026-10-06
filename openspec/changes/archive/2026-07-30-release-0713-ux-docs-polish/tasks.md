## 1. UI Refactoring

- [x] 1.1 Update `frontend/components/admin/frbr-editor.tsx` header: replace the four FRBR level tabs with a Shadcn `Select` component.
- [x] 1.2 Update `frontend/components/admin/frbr-editor.tsx` type selector: replace the native `<select>` dropdown with a Shadcn `Command` (Combobox) component for manifestation types.
- [x] 1.3 Update `frontend/components/admin/escalation-queue.tsx` to clearly display the target entity UUID and title/name in the escalation card to prevent IDOR manipulation confusion.

## 2. Documentation Updates

- [x] 2.1 Create `docs/AI_COVERS.md` to document the AI cover generation script (`scripts/generate_ai_covers.py`) and its operational flags (`--batch-all-unwatermarked`, `--dry-run`, `--watermark-only`, `--force-retry`).
- [x] 2.2 Update `README.md` to include a brief overview of the AI cover generation process and link to `docs/AI_COVERS.md`.
- [x] 2.3 Update `Makefile` to include targets for running the AI cover generation script with standard flags.

## 3. Tech Debt & Spec Backfill

- [x] 3.1 Replace "TBD - created by archiving change..." placeholder text with proper Purpose sections for all 13 OpenSpec spec files located in `openspec/specs/*/spec.md` (generated from the v0.7.13 archive).

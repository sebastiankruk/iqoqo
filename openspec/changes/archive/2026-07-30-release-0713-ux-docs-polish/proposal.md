## Why

The v0.7.13 release reviews identified several user experience (UX) bottlenecks, documentation gaps, and a low-severity IDOR clarity issue. Fixing these issues now ensures our UI is usable, our security posture is clear, and our project documentation meets standard hygiene practices before the next major release.

## What Changes

- **FRBR Editor Button Density**: Replace the 4 horizontal tabs for FRBR levels with a Shadcn `Select` component in the header, reducing button count to comply with heuristics.
- **Manifestation Type Cognitive Overload**: Replace the native `<select>` dropdown (24 options) with a Shadcn `Command` (Combobox) to allow keyboard-first filtering and searchability.
- **OpenSpec Spec Placeholders**: Replace "TBD - created by archiving change..." placeholder text with proper Purpose sections for all 13 OpenSpec spec files generated in the v0.7.13 archive.
- **AI Cover CLI Documentation**: Document flags for `scripts/generate_ai_covers.py` (`--batch-all-unwatermarked`, `--dry-run`, `--watermark-only`, `--force-retry`) in `README.md`, `docs/AI_COVERS.md`, and Makefile targets.
- **IDOR UI Clarity**: Update the Custodian escalation review screen to clearly display target entity details, preventing IDOR manipulation confusion.

## Capabilities

### New Capabilities

- `ai-cover-cli-docs`: Comprehensive documentation for the AI Cover generation CLI tools and scripts.

### Modified Capabilities

- `frbr-ui-type-change`: Update FRBR Editor header to use Select instead of tabs, and replace Manifestation type select with Command (Combobox).
- `batch-watermarking`: Update documentation requirements to include flags for the AI covers script.
- `escalation-queue-ui`: Improve UI clarity by displaying target entity details during custodian review to prevent IDOR manipulation.

## Impact

- **UI/Frontend**: `frontend/components/admin/frbr-editor.tsx`, `frontend/components/admin/escalation-queue.tsx`.
- **Docs**: `README.md`, `docs/AI_COVERS.md`, `Makefile`, and `openspec/specs/*/spec.md` (13 files).
- **Dependencies**: Uses existing Shadcn components (`Select`, `Command`).

## Context

Following the v0.7.13 release, multiple UX reviews identified points of friction. The FRBR editor is too dense, violating the rule of maximum 4 buttons per header, and the manifestation type select is overwhelming. Security review found the IDOR mitigation UI needs better clarity on the custodian escalation screen. Finally, we need to address technical documentation debt regarding AI covers and placeholder specs created during the v0.7.13 archive.

## Goals / Non-Goals

**Goals:**

- Improve FRBR Editor layout by consolidating tabs into a Shadcn `Select`.
- Enhance the manifestation type input using Shadcn `Command` for searchability.
- Clear technical debt in OpenSpec specs by replacing "TBD" placeholders.
- Document AI cover scripts thoroughly.
- Add explicit target entity details in the custodian review queue.

**Non-Goals:**

- Implementing board game expansion rules or mechanics vocabulary (deferred).
- Adding inventory tag columns (deferred).
- RDF/JSON-LD export support (deferred).

## Decisions

- **FRBR Editor Button Density**: We will replace the four FRBR tabs (Work, Expression, Manifestation, Item) in `frontend/components/admin/frbr-editor.tsx` with a single Shadcn `Select` element. This reduces the button count from 5 to 2.
- **Manifestation Dropdown**: The native `<select>` in `frbr-editor.tsx` for manifestation type will be replaced with Shadcn `Command`. This leverages our existing component library to give users keyboard-first filtering without adding external dependencies.
- **IDOR UI Clarity**: The `frontend/components/admin/escalation-queue.tsx` will be modified to display the target entity UUID and brief details (e.g., name/title) before allowing the custodian to approve/reject an escalation.
- **AI Cover Docs**: Documentation will be placed directly in the main `README.md` (brief overview), with a detailed `docs/AI_COVERS.md` and standard `Makefile` targets.
- **Spec Updates**: Direct modification of the 13 `openspec/specs/*/spec.md` files in the repository to replace placeholder text with descriptive purpose sections.

## Risks / Trade-offs

- [Risk] Replacing tabs with a `Select` may hide the FRBR levels from users who aren't familiar with the dropdown. -> Mitigation: Add a clear placeholder/default value indicating the current FRBR level context.
- [Risk] Missing Shadcn Command components in `frbr-editor.tsx`. -> Mitigation: Ensure `Command`, `CommandInput`, `CommandList`, `CommandEmpty`, `CommandGroup`, `CommandItem` are imported from `@/components/ui/command`.

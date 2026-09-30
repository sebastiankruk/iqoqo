## Context

Currently, the `ManifestationEditor` in `frbr-editor.tsx` hardcodes the dropdown values for manifestation `type`. Formats defined in `shared/taxonomy.yaml` (such as `bluray_audio`) are not accessible through this dropdown, forcing users to manually enter a `format` key in the Dynamic Metadata section. This lacks synchronization with the actual domain definitions (taxonomy) and creates friction.
The taxonomy API (`/api/taxonomy`) already serves taxonomy data, which can be fetched to populate this dropdown.

## Goals / Non-Goals

**Goals:**

- Replace the hardcoded `type` select dropdown with a dynamically populated select widget.
- Group the formats under their parent media categories (e.g., Music, Movie) using `<optgroup>` tags.
- Create tests ensuring the select list and `taxonomy.yaml` stay perfectly in sync.

**Non-Goals:**

- Do not migrate or refactor other parts of the FRBR Editor beyond the `ManifestationEditor` type select.
- Do not redesign the entire taxonomy system; rely on the existing `/api/taxonomy` output or a utility function if it's available.

## Decisions

- **Use `<optgroup>` for categorization:** By grouping formats under their broad categories, we maintain the UX flow and make it easy to find specific formats like "Blu-ray Pure Audio".
- **Fetch from existing taxonomy types/API:** We will use the existing `taxonomy` types or fetch the taxonomy at runtime. Since this is an admin component, fetching the taxonomy configuration on mount (or using a pre-fetched context) is appropriate.
- **Sync Testing:** We will add a frontend test in Vitest that asserts the taxonomy entries map correctly to the dropdown options.

## Risks / Trade-offs

- **Risk:** Existing hardcoded values like "Comic Book" might not map 1:1 if the backend taxonomy format id/label changes.
  **Mitigation:** Verify format mappings when replacing the hardcoded list. Ensure the component correctly handles legacy string values by safely falling back or migrating them upon save.

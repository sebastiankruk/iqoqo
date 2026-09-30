## Why

Currently, the FRBR Editor's Manifestation type selection relies on a hardcoded list of broad media categories rather than reading the specific formats defined in `shared/taxonomy.yaml` (such as `bluray_audio`). This causes massive UX friction because adding a specific format requires manually injecting a string in the Dynamic Metadata key-value inputs. We need to introduce a dynamic, taxonomy-driven grouped select widget to fix this gap.

## What Changes

- Replaces the hardcoded type select in `ManifestationEditor` (`frbr-editor.tsx`) with a taxonomy-driven grouped select component.
- The new select widget will group specific formats under their respective broad media categories (e.g., Music -> Blu-ray Pure Audio).
- Adds tests to ensure the select list items stay perfectly in sync with `shared/taxonomy.yaml` entries.
- Integrates the existing taxonomy sync script (used in `/api/taxonomy`) to provide format lists directly to the FRBR editor.

## Capabilities

### New Capabilities

- `dynamic-frbr-manifestation-formats`: Introduce dynamic format selection in the FRBR Editor mapped from `taxonomy.yaml`.

### Modified Capabilities

## Impact

- **Frontend:** `frontend/components/admin/frbr-editor.tsx`
- **Tests:** Add unit tests to ensure that the taxonomy entries match the editor options.

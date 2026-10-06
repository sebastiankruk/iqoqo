## 1. Frontend Implementation

- [x] 1.1 Fetch or statically load the taxonomy groupings in `frontend/components/admin/frbr-editor.tsx`.
- [x] 1.2 Refactor the `type` select dropdown in `ManifestationEditor` to use `<optgroup>` containing the taxonomy formats.
- [x] 1.3 Ensure the `ManifestationEditor` properly handles backwards compatibility if an old format is selected or if no matching format exists.

## 2. Testing and Validation

- [x] 2.1 Add a unit test to verify that the `ManifestationEditor` dropdown lists correctly map to the taxonomy structure defined in `shared/taxonomy.yaml`.
- [x] 2.2 Validate that selecting a format (like `bluray_audio`) saves correctly and associates with the correct category.

## 1. Component Implementation

- [ ] 1.1 Create `frontend/components/ui/rich-text.tsx` supporting entity decoding, DOMPurify sanitization, and Markdown formatting; verify with unit test
- [ ] 1.2 Replace ad-hoc description rendering in `frontend/components/item/extended-metadata.tsx` with `<RichText content={description} />`; verify visual rendering
- [ ] 1.3 Replace plain text rendering in `frontend/components/item/item-timeline.tsx` with `<RichText content={description} />`; verify visual rendering

## 2. Backend Sanitization & Testing

- [ ] 2.1 Update `app/core/frbr_service.py` to sanitize incoming metadata `description` fields via `bleach.clean()` with whitelisted tags; verify with pytest in `tests/test_frbr_sanitization.py`
- [ ] 2.2 Add Vitest tests in `frontend/__tests__/components/ui/rich-text.test.tsx` verifying HTML entities, Markdown syntax, mixed markup, and XSS payload neutralization
- [ ] 2.3 Verify item description rendering against test fixtures representing item 2027

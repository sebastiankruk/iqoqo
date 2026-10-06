## 1. Feedback API Security Hardening

- [x] 1.1 Add `@limiter.limit("60 per minute")` decorator to `list_feedback()` (GET `/api/feedback`) in `app/api/feedback.py`.
- [x] 1.2 Add `@limiter.limit("60 per minute")` decorator to `get_feedback_item()` (GET `/api/feedback/<id>`) in `app/api/feedback.py`.
- [x] 1.3 Add `@limiter.limit("30 per minute")` decorator to `update_feedback()` (PATCH `/api/feedback/<id>`) in `app/api/feedback.py`.
- [x] 1.4 Clamp pagination parameters: `page = max(1, request.args.get("page", 1, type=int))` and `per_page = max(1, min(request.args.get("per_page", 20, type=int), 100))` in `list_feedback()`.
- [x] 1.5 Add upload count cap: insert `uploads = request.files.getlist("screenshots")` followed by `if len(uploads) > 5: return jsonify({"success": False, "error": "Maximum 5 screenshots allowed per ticket"}), 400` before the processing loop in `submit_feedback()`.
- [x] 1.6 Add closed-ticket comment guard: insert `if item.status == "closed": return jsonify({"success": False, "error": "Cannot add comments to a closed ticket"}), 400` before the comment append logic in `update_feedback()`.

## 2. Feedback API Tests

- [x] 2.1 Write pytest test for `GET /api/feedback` rate limiting — verify 429 response after exceeding 60 requests per minute.
- [x] 2.2 Write pytest test for negative pagination clamping — verify `page=-1` returns first page, `per_page=500` clamps to 100 results.
- [x] 2.3 Write pytest test for upload count cap — verify submitting 6+ screenshots returns HTTP 400 with expected error message.
- [x] 2.4 Write pytest test for closed-ticket comment guard — verify PATCH with comment on a closed ticket returns HTTP 400.

## 3. Scanner UX Escape Hatch

- [x] 3.1 Add a "Skip and enter manually" text-link button inside the z-30 loading overlay in `frontend/components/scanner/bottom-sheet.tsx`, wired to `onShowManualForm(lastSearchedBarcode)`.
- [x] 3.2 Add i18n translation key for "Skip and enter manually" to `frontend/messages/en.json` and `frontend/messages/pl.json` (sentence case for Polish).
- [x] 3.3 Write Vitest unit test verifying the cancel button renders inside the overlay and calls the manual form callback when clicked.

## 4. Nginx Payload Alignment

- [x] 4.1 Add `client_max_body_size 50M;` directive to the main `server` block in `deploy/nginx.conf`.
- [x] 4.2 Add deployment note in `docs/CHANGELOG.md` under v0.7.15 noting the required Nginx body size update for custom deployments.

## 5. Dashboard Test Robustness

- [x] 5.1 Add `data-testid="stats-scroll-container"` attribute to the flex-nowrap scrolling div in `frontend/components/dashboard/stats-cards.tsx`.
- [x] 5.2 Update `frontend/__tests__/components/dashboard/stats-cards.test.tsx` to replace `container.querySelector(".overflow-x-auto.flex-nowrap")` with `screen.getByTestId("stats-scroll-container")`.

## 6. OpenSpec Purpose Text Cleanup

- [x] 6.1 Replace "TBD" Purpose section in `openspec/specs/scanner-visual-waiting/spec.md` with: "This specification defines the animated visual feedback shown to users during asynchronous scanner API lookups, including the escape mechanism for cancelling in-progress searches."
- [x] 6.2 Replace "TBD" Purpose section in `openspec/specs/scanner-error-fallback/spec.md` with: "This specification defines the graceful degradation path from automated scanner lookups to manual barcode entry when API responses fail or time out."

## 7. Feedback Attachment Display Fix

- [x] 7.1 In `frontend/components/feedback/feedback-detail-modal.tsx`, replace `aspect-video` + `object-cover` on attachment thumbnails with a fixed-height container (`h-32 w-full`) using `object-contain` to preserve vertical screenshot aspect ratios.
- [x] 7.2 Write Vitest test verifying attachment images render with `object-contain` class instead of `object-cover`.

## 8. Verification & Formatting

- [x] 8.1 Run `make format-python` to format backend changes.
- [x] 8.2 Run `make format-js` to format frontend changes.
- [x] 8.3 Run `make lint` and verify zero errors.
- [x] 8.4 Run `make test` and verify all suites pass.

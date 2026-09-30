## 1. Adjust Endpoint Validation Logic

- [x] 1.1 Update `_validate_screenshot_access` in `app/api/feedback.py` to query the `FeedbackItem` containing the screenshot filename in its attachments. Verify this logic works locally.
- [x] 1.2 In `_validate_screenshot_access`, change the access check to allow access if the user is an admin (`_can_admin_tickets(user)`) or if they are the owner of the `FeedbackItem` or if they have read access through another mechanism (if applicable). Verify that the updated code avoids purely checking the user's item list and instead evaluates read access per ticket.

## 2. Update Tests

- [x] 2.1 Update or create tests in `tests/test_feedback_security.py` (or existing security tests like `tests/test_feedback_tickets.py` if `test_feedback_security.py` doesn't exist) to verify that a non-admin ticket author can access attached screenshots without IDOR failures. Run tests to verify they pass.
- [x] 2.2 Add tests to verify that assigned custodians (users with the appropriate read access) can also access the screenshots successfully. Verify this by running the relevant test suite.
- [x] 2.3 Ensure tests exist that verify unauthorized users still receive a 403 or 404 response when attempting to access screenshots directly. Run pytest to ensure these tests pass.

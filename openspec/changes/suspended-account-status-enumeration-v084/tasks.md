# Tasks: suspended-account status enumeration

**Nothing in this list may start until the review in `proposal.md` is answered.** Task 0 is a gate, not work.

## 0. Review gate

- [ ] 0.1 Confirm the D1 decision (see `design.md`): keep the suspension signal in the body and drop it from the status, **or** make the body fully generic too. Record the choice in this file, dated, so the test in 3.2 is written against a settled decision rather than a guess.

## 1. Verify the premise again

- [ ] 1.1 Re-verify that the account does not exist, and the account is suspended, really do return different status codes on the current `release/0.8.2`. Written down as a reproduction before the fix, because the finding came from reading code rather than observing the endpoint.
- [ ] 1.2 Re-run the frontend grep for any consumer branching on 403 from `/api/auth/login`. C18 established none existed; do not assume it is still true.
- [ ] 1.3 Confirm no other caller of `local_login` or of `is_active`-based response handling is affected (scripts, tests, the E2E suite).

## 2. Implement

- [ ] 2.1 Change `app/api/auth.py:local_login` so the suspended case returns the same status as the invalid-credentials case, keeping the `is_active` check strictly **after** password verification.
- [ ] 2.2 Carry the suspension reason in the response body per the D1 outcome chosen in 0.1. If the identical-body option was chosen, record where — or whether — a suspended user learns their account exists.
- [ ] 2.3 Update the `local_login` docstring. It already claims the response "does not reveal whether an account exists"; extend it to state that the **status code** carries no account state, so the next reader does not "improve" the message back into an oracle.

## 3. Tests

- [ ] 3.1 Add the three-way status test from `design.md` D4: unknown email → 401, registered + wrong password → 401, registered + correct password + suspended → 401. Assert the statuses are *equal*, not that a particular body is absent.
- [ ] 3.2 Assert the 200 path still requires a correct password on an active account, so the fix cannot be "make everything 401".
- [ ] 3.3 **Confirm the C18 4.6 timing test in `tests/test_auth_security.py` still passes unmodified.** If it has to change for this work to go in, that means the `is_active` check moved and the timing oracle is back — stop and reconsider rather than adjusting the test.

## 4. Verify

- [ ] 4.1 Revert the fix and confirm 3.1 fails, then restore. The new test must be shown to fail against the unfixed endpoint.
- [ ] 4.2 `pytest tests/test_auth_security.py tests/test_auth.py` green.
- [ ] 4.3 Full backend suite green.
- [ ] 4.4 Record the outcome in `docs/CHANGELOG.md`, stating plainly that this narrows an enumeration channel rather than closing it, if the body retains the signal.

## 5. Notes for whoever picks this up

- Do **not** cite the 5-per-minute rate limit as a mitigation. It bounds enumeration rate, not its existence (`design.md` D2).
- Do **not** move the `is_active` check before the password comparison. It reads as a natural simplification and reintroduces the timing oracle fixed in v0.8.2 (`design.md` Risks).

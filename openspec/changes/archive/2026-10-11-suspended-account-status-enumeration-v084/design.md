# Design: suspended-account status enumeration

**See `proposal.md` — Why** for the motivation and the enumerated-account finding. This document covers only the mechanics and the decision that must be made before any code is written.

## Context

The three responses of `local_login` today:

| Condition | Status | Body |
| --- | --- | --- |
| No such account, or wrong password | 401 | `{"error": "Invalid credentials"}` |
| Correct password, `is_active` false | 403 | `{"error": "Suspended"}` |
| Correct password, active | 200 | `{"token": …, "user": {…}}` |

Two invariants constrain any fix, both established by v0.8.2:

- **The `is_active` check must stay after the password check.** Moving it earlier lets an attacker distinguish "no such account" from "suspended account" in *response time* rather than status code — reintroducing exactly the oracle C18 4.6 closed by making the no-account path perform a full password verification.
- **The status code must become identical across the 401 and 403 cases.** Once they match, the body becomes the only remaining channel, and the body is already generic for the failure the attacker cares about.

## Goals / Non-Goals

### Goals

- Make the status code for "account does not exist / wrong password" and "account suspended" indistinguishable.
- Keep the `is_active` check strictly after password verification.
- Leave the 200 path untouched.

### Non-Goals

- Changing the timing profile of any path. C18 4.6 measured it at −0.28 ms and that is the floor.
- Changing token revocation, session handling, or the blocklist.
- Deciding what the suspended user is told. That is the open decision; the design is written so either answer fits.

## Decisions

### D1: Where the suspension signal lives

**Proposed: keep the signal in the body, drop it from the status.**

`return jsonify({"error": "Invalid credentials"}), 401` for both cases, with the reason carried in the body only when the password was correct — e.g. `{"error": "Account suspended", "suspended": true}`.

**Alternative: identical body as well.** Fully generic; costs the suspended user any clue at all.

**Why the proposed option is a compromise and not a clean win:** it moves the oracle from status code to body, which a determined attacker can still read. It is a *narrowing* of the channel, not a closure. It is proposed because status codes are the channel automated tooling reads, and because it preserves the only signal that lets a real user understand what happened.

**This is the decision the review must settle.** If the reviewer prefers strict genericity, D1 becomes the identical-body option and the suspended user gets no message — in which case the suspension state needs to be surfaced somewhere else, or not at all.

### D2: Rate limiting is not a mitigation

`@limiter.limit("5 per minute")` is already on `/login`. It bounds the *rate* of enumeration to 5 probes per address per minute; it does not remove the channel. Do not cite it as a reason to leave the oracle open.

### D3: No frontend change is expected

Verified during C18: `grep` for `Suspended` across the frontend returns only `components/admin/user-management.tsx` (an admin-facing status label and `<option>`), which is unrelated to the login response. The login page renders whatever `error` the body carries. So the change is confined to `app/api/auth.py` plus a test.

**If D1 lands with a new body field, confirm the login form surfaces it.** The form renders a generic error today; a body it ignores would make the change invisible.

### D4: Test shape — assert the statuses match, not that a body is absent

The regression test should be:

1. unknown email → 401
2. registered + wrong password → 401
3. registered + correct password + suspended → **401**

and a second test asserting the 200 path still requires a correct password on an active account. Asserting equality between cases 1 and 3 is the point; asserting on exact message text would make the test brittle to wording and would encode whichever D1 answer was chosen as permanent.

The C18 4.6 timing test lives in `tests/test_auth_security.py` and must keep passing unchanged — it is the guard on D1's "after the password" ordering.

## Risks / Trade-offs

- **[Risk] Moving `is_active` earlier during implementation reopens the timing oracle.** → Mitigation: the ordering constraint is stated in D1 and is covered by the existing timing test in `tests/test_auth_security.py`. If that test ever needs changing to accommodate this change, stop.
- **[Risk] A suspended user is now told "Invalid credentials" and starts a password-reset loop.** → Mitigation: this is the cost of D1 as proposed. It is the reason D1 is a review question rather than a decision, and the reason the "suspended" body variant is in the proposal rather than assumed.
- **[Risk] Any consumer branching on 403 from this endpoint breaks silently.** → Mitigation: verified absent in the frontend during C18; re-verify at implementation time with a fresh grep rather than trusting that audit, since a lot has changed.
- **[Risk] The change reads as "hiding useful information" to a future maintainer.** → Mitigation: the docstring currently claims the response does not reveal account existence, so this change makes the code match its stated intent. That claim should be kept and extended to say *why* the status code carries no account state.

## Migration Plan

Single-commit change, no migration, no configuration, no data. Revert is a clean revert.

## Open Questions

None that can be deferred. The remaining question — D1 — would change the specs, so it is raised for review in `proposal.md` rather than parked here.

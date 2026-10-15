## Why

`POST /api/auth/login` distinguishes three outcomes with three status codes, and one of them reveals whether an email is registered:

```python
# app/api/auth.py, local_login
if not _verify_login_password(user, password):
    return jsonify({"error": "Invalid credentials"}), 401
if not user.is_active:
    return jsonify({"error": "Suspended"}), 403
```

**An unknown address returns 401. A suspended account returns 403.** Both bodies are distinct, so an attacker can enumerate registered emails by watching the status code instead of the timing — and the timing channel was closed in v0.8.2 by C18 (4.6), which fixed the 0.00 ms-vs-90.40 ms oracle without noticing this second oracle on the adjacent line.

The function's own docstring states the intent this contradicts:

> The password is verified against a hash, and the response is generic on failure
> so it does not reveal whether an account exists.

The response body *is* generic. The status code is not, and status codes are what an attacker reads.

**Why this was not fixed in v0.8.2.** C18 found it, recorded it, and deliberately deferred it. The blocker is a product decision, not a technical one:

- Collapsing 403 to 401 means a genuinely suspended user signs in, is told "Invalid credentials", and has no idea the account exists or that it was suspended. They would most likely conclude they forgot their password and start a password-reset loop against a real account.
- Keeping 403 means the enumeration oracle stays open. `is_active` is set by an administrator, so the affected population is exactly the set of accounts an admin has acted on.

Both are defensible; they trade a security property against user-facing clarity, and that is the user's call rather than a sweep's.

## What Changes

- **Nothing is implemented without explicit review.** This change exists to request that decision. No code is touched until the approach below is agreed.
- The proposed default is to collapse the 403 into the 401 path and carry the reason in the response body rather than the status code, so status stops being the oracle while the message survives for the legitimate user.
- The trade-off above is stated plainly and the alternative (keep 403, accept the oracle, and document the residual risk) is recorded as a live option rather than a rejected one.

## Impact

- **Affected capability:** `auth` (sign-in).
- **Behaviour change:** the status code for a suspended account, and therefore any client that branches on 403 from `/api/auth/login`.
- **Security:** closes an account-enumeration channel; does not weaken authentication. A suspended account still cannot obtain a token.
- **Blast radius:** one endpoint plus whatever frontend handles that 403 today. Verified during C18 that **no frontend code branches on it** — the only "Suspended" strings in the codebase are in admin user-management, unrelated to login — so the visible change is limited to the message a suspended user sees.
- **No schema change, no migration, no data change.**

## Review requested

Before this is implemented, please confirm:

1. **Collapse to 401, or keep 403?** The recommendation is 401 with the reason in the body, on the grounds that status codes are read by machines and bodies by humans, and enumeration is the machine-readable channel. Keeping 403 is defensible if preserving the "your account is suspended" signal matters more.
2. **If collapsed, what should the user actually see?** "Invalid credentials" is actively misleading for a real account. A body like `{"error": "Invalid credentials"}` with no hint preserves security but costs clarity; naming the suspension restores clarity and reintroduces the oracle in the body, which is a strictly worse version of the current problem.
3. **Should an inactive account be checked before or after the password?** Checking before would restore the enumeration oracle in the response *time*, undoing C18 4.6. It must stay after.

Point 3 is a trap worth stating explicitly: the obvious implementation of "tell suspended users the truth" reintroduces the timing bug just fixed.

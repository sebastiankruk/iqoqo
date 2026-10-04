# Email Setup

iQoQo sends transactional email for two things:

- **Verifying your email address**, which you must do before you can delete your account.
- **Confirming account deletion.** A link goes to your verified address; the account is removed only after you open it and confirm.

Nothing else sends mail. No digests, no notifications, no third-party relay. If you never configure mail, everything else in iQoQo works normally — you just cannot delete an account, and the UI says so.

## Quick start

### 1. Add the settings to `.env`

```bash
MAIL_ENABLED=true
MAIL_HOST=smtp.example.com
MAIL_PORT=587
MAIL_USERNAME=iqoqo@example.com
MAIL_PASSWORD=your-app-password
MAIL_USE_TLS=true
MAIL_FROM_ADDRESS=iqoqo@example.com
PUBLIC_APP_URL=https://iqoqo.example.com
```

Restart the backend. There is no connection test at startup — see [Why nothing connects at boot](#why-nothing-connects-at-boot).

### 2. Send yourself a verification link

Sign in, open **Profile → Email Address → Send verification link**, and check the address. If it does not arrive, the settings are wrong or the relay is refusing the sender address.

### 3. Verify your own mail first

Before you rely on account deletion, confirm that you can complete the whole loop on your own instance. Deleting an account is irreversible, and it should not be the first time you discover that the relay rejects a particular address.

## Settings

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `MAIL_ENABLED` | yes | `false` | Master switch. When false, the mail features return a clear "not configured" error. |
| `MAIL_HOST` | yes | — | Bare hostname or IP. A URL is rejected, because a typo here otherwise surfaces as a confusing port error. |
| `MAIL_PORT` | no | `587` | `587` for STARTTLS, `465` for implicit TLS. |
| `MAIL_USERNAME` | no | — | Omit for an open relay on localhost. |
| `MAIL_PASSWORD` | no | — | Fernet-encrypted at rest once set from the admin UI. |
| `MAIL_USE_TLS` | no | `true` | Negotiate STARTTLS. A relay that does not offer it **fails the send** rather than continuing in plaintext. |
| `MAIL_USE_SSL` | no | `false` | Implicit TLS. Mutually exclusive with `MAIL_USE_TLS`; enabling both is a configuration error. |
| `MAIL_FROM_ADDRESS` | yes | — | The only permitted sender. Must be a plain address your relay will send as. |
| `MAIL_FROM_NAME` | no | `iQoQo` | Display name paired with the address. |
| `MAIL_TIMEOUT_SECONDS` | no | `10` | Clamped to 1–120. Bounds the relay connection. |
| `PUBLIC_APP_URL` | yes | — | The origin in emailed links. Must be `https://` outside localhost. |
| `MAIL_TRANSPORT` | no | `smtp` | `memory` records messages instead of sending them. Development and e2e only. |

### Setting the password from the admin UI

`MAIL_PASSWORD` is one of the keys stored encrypted. Set it under **Admin → Settings → API keys** (or the Internal category) rather than in `.env`, and it is written to `instance_settings` as a Fernet envelope using `SECRET_KEY`.

> Rotating `SECRET_KEY` makes existing stored values unreadable. Run `make migrate-secrets` to re-encrypt them from `.env`. See [SECURITY.md](SECURITY.md).

## Provider notes

Any provider reachable over SMTP works — there is no vendor SDK, deliberately, so self-hosted deployments are not locked to one company.

**Gmail / Google Workspace.** Ordinary accounts cap sending at a few hundred messages a day and will reject mail from an unverified `MAIL_FROM_ADDRESS`. Use a Workspace account with an app password, and expect the daily cap.

**A local Postfix.** Common for self-hosting. `MAIL_HOST=127.0.0.1`, `MAIL_PORT=25`, `MAIL_USERNAME` and `MAIL_PASSWORD` unset. Prefer it for privacy: the mail never leaves the host.

**A managed relay.** Point `MAIL_HOST`/`MAIL_PORT` at it. Some providers require `MAIL_USE_TLS=false` because they terminate TLS on a non-standard port; that configuration sends in plaintext, so only use it on a trusted network path.

## Troubleshooting

**"This instance is not configured to send mail."** `MAIL_ENABLED` is not true, or the instance is configured but one of the required values is missing. Check the backend logs — the error names the specific setting at fault rather than saying "mail is broken".

**The request returns 503 but mail is configured.** `PUBLIC_APP_URL` is probably unset. Without a known public origin iQoQo refuses to generate a link, because it will not guess one and mail `http://localhost/...` to a real person.

**No mail arrives, no error.** Almost always a relay-side rejection — greylisting, SPF/DKIM failure, or a blocked sender address. iQoQo's logs record a successful hand-off to the relay, not a delivery confirmation; only the relay knows the message arrived. For self-hosted diagnosis, run a local relay with an unthrottled destination and watch its logs.

**Links in the mail go to the wrong host.** `PUBLIC_APP_URL` is set incorrectly. It is never taken from the request, on purpose: a link built from the `Host` header is whatever an attacker chose to send, and for a mailbox-control token that means handing it to a domain of their choosing.

## Behaviour worth knowing

### Why nothing connects at boot

An instance with no relay must still start, serve its catalogue, and accept logins. A missing mail server is an operator problem to fix, not a reason to refuse to boot. The consequence is that a misconfiguration surfaces on the first send rather than at startup — which is why every failure names the setting at fault.

### Why there is a timeout

Every send is bounded by `MAIL_TIMEOUT_SECONDS`. An unreachable SMTP server that never responds would otherwise hold a gunicorn worker open indefinitely. Since one hung request per worker is a full outage, the timeout is a deliberate availability control, not a nicety.

### What verification does and does not mean

Confirming an address proves you can receive mail there. It is **not** a second sign-in and is not treated as one. Someone who has your password *and* access to your mailbox could complete a deletion — so deletion also requires an active session for your account at the moment you confirm.

### Opening the link does nothing by itself

Mail clients preview links, security scanners fetch every URL in an incoming message, and browsers prefetch. Opening the confirmation link therefore only ever renders a page. Nothing is deleted until you submit the form on that page while signed in.

### Tokens expire after 30 minutes

Deletion links are valid for 30 minutes and work once. Requesting a new link invalidates the previous one. Verification links are valid for 24 hours.

### Tokens are never logged

Account-lifecycle tokens are stored only as a keyed digest, and a redaction filter installed on the root log handler strips `token=` query parameters, JWT-shaped strings, and your signing secrets from every log line. A token cannot be recovered from a log backup or from a database dump.

## Verifying the setup

The automated suite covers the whole flow against a capture transport, with no network:

```bash
make test-backend           # or: .venv/bin/pytest tests/test_account_deletion.py
cd frontend && npx vitest run __tests__/components/profile
```

To exercise it without a relay, set `MAIL_TRANSPORT=memory` and inspect what would have been sent.

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

**The mail server could not be reached or refused the message.** The relay was contacted and would not take the message. This is deliberately reported differently from a configuration problem, because the causes and fixes differ: one needs a relay that accepts the message, the other needs `MAIL_HOST` set at all. The log line names the underlying SMTP error class (`SMTPRecipientsRefused`, `SMTPAuthenticationError`, and so on); read it there rather than guessing from the message.

If this appeared only after a stack restart on a self-hosted setup, check whether your SMTP sink was detached from the project network — see [Trying it by hand](#trying-it-by-hand).

**Links in the mail go to the wrong host.** `PUBLIC_APP_URL` is set incorrectly. It is never taken from the request, on purpose: a link built from the `Host` header is whatever an attacker chose to send, and for a mailbox-control token that means handing it to a domain of their choosing.

## Behaviour worth knowing

### Why nothing connects at boot

An instance with no relay must still start, serve its catalogue, and accept logins. A missing mail server is an operator problem to fix, not a reason to refuse to boot. The consequence is that a misconfiguration surfaces on the first send rather than at startup — which is why every failure names the setting at fault.

### Why there is a timeout

Every send is bounded by `MAIL_TIMEOUT_SECONDS`. An unreachable SMTP server that never responds would otherwise hold a gunicorn worker open indefinitely. Since one hung request per worker is a full outage, the timeout is a deliberate availability control, not a nicety.

### What verification does and does not mean

Confirming an address proves you can receive mail there. It is **not** a second sign-in and is not treated as one. Someone who has your password *and* access to your mailbox could complete a deletion — so deletion also requires an active session for your account at the moment you confirm.

### Opening the link does nothing by itself

Mail clients preview links, security scanners fetch every URL in an incoming message, and browsers prefetch. Opening the confirmation link therefore only ever renders a page. Nothing is deleted until you press the confirmation button on that page while signed in.

### The confirmation pages are part of the iqoqo site

The link points at an ordinary page of the application — you will see the normal iqoqo header, navigation and footer, because that is exactly what is being rendered. A confirmation page with no branding, no navigation and its own styling, arriving by email, is indistinguishable from a phishing page and is the reason these screens are frontend routes rather than server-rendered responses. If the page you land on does not look like the rest of iqoqo, stop.

These routes are also served with `Referrer-Policy: no-referrer`, so the token in the address bar is not passed on to anything else the page loads, and with `Cache-Control: no-store` so it cannot be replayed from a cache or the back button.

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

### Trying it by hand

A real relay is the only honest test — it catches header bugs and encoding problems a stub hides. Mailpit accepts any mail and shows it in a web UI, with nothing sent externally:

```bash
docker run -d --name iqoqo-mailpit -p 1025:1025 -p 8025:8025 axllent/mailpit
```

Then in `.env`:

```bash
MAIL_ENABLED=true
MAIL_HOST=mailpit
MAIL_PORT=1025
MAIL_USE_TLS=false
MAIL_FROM_ADDRESS=iqoqo@example.invalid
PUBLIC_APP_URL=https://iqoqo.example.com
```

**If the containers cannot reach `mailpit`**, Mailpit is on the Docker default bridge while the stack is on its own project network. Attach it:

```bash
docker network connect --alias mailpit iqoqo-preview_default iqoqo-mailpit
```

Two things about that command:

- The `--alias` is required. Without it Docker resolves the *container name* (`iqoqo-mailpit`), not `mailpit`, so `MAIL_HOST=mailpit` fails to resolve.
- **Re-run it after every `preview-down`/`make preview-down`.** Removing the stack deletes the project network, which silently detaches Mailpit. Symptom: the first email works, everything after a stack restart fails with the mail-server-refused error while the configuration is still correct.

Verify reachability from inside the stack before concluding anything else:

```bash
docker exec iqoqo-preview-web-1 python -c "import smtplib; s=smtplib.SMTP('mailpit',1025,timeout=8); print(s.ehlo()[0]); s.quit()"
```

### What `MAIL_TRANSPORT=memory` is for

It swaps in a recorder that keeps messages in memory for the lifetime of the process. It exists for tests, which construct the recorder directly — **nothing exposes what it captured**, so it is not a way to inspect mail. Use Mailpit instead.

### Walking the flow

Sign in → **Profile → Email Address → Send verification link** → open the link in Mailpit → press **Confirm this address** → **Delete Account** → open the link → press **Yes, permanently delete my account**.

Three properties are worth checking by hand, because they are what the design rests on and they are easier to confirm than to infer:

- Open a confirmation link twice, or let browser prefetch fetch it. Nothing is consumed and nothing is deleted.
- Open a deletion link while signed in as a different account. It refuses, and both accounts are untouched — and the real owner's link still works afterwards.
- Load a confirmation link with JavaScript disabled or with the network tab open. The GET that reports the link's state is read-only; the delete is a separate POST that you have to trigger.

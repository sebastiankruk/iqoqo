## Context

See `proposal.md` for motivation. Home-lab builders and federation node operators need a single guided command to bootstrap `.env`, generate cryptographic secrets, and run pre-sync/preview verification (`iqopresync`) before peering with `iqoqo.cc`.

## Goals / Non-Goals

**Goals:**
- Deliver a zero-dependency Python 3 standard-library CLI wizard (`scripts/iqoqo_installer.py`) so it runs on any bare Ubuntu/macOS host before `.venv` or Docker containers are even initialized.
- Enforce `security-auditor` and `devops-observability-expert` constraints: `os.chmod(env_path, 0o600)`, `secrets.token_urlsafe(48)` for `SECRET_KEY`/`JWT_SECRET_KEY`, zero default/hardcoded passwords, and interactive confirmation before overwriting an existing production `.env`.
- Integrate `iqopresync` checks and package the standalone installer artifact + SHA-256 checksum in GitHub Actions CI.

**Non-Goals:**
- Replacing Docker Compose or `scripts/iqoqo-status.sh` (`iqopresync` complements and delegates to `iqoqo-status.sh` when containers are up).

## Decisions

### 1. Pure Standard-Library Python CLI (`scripts/iqoqo_installer.py`)
* **Decision:** Implement `scripts/iqoqo_installer.py` using only Python standard library modules (`argparse`, `getpass`, `os`, `pathlib`, `secrets`, `shutil`, `stat`, `subprocess`, `urllib.request`) and expose `make install-wizard` and `make presync-check` in `Makefile`.
* **Rationale (SRE & Portability):** A fresh VPS or home-lab machine may not have `venv` packages installed on host Python yet. A stdlib-only script runs anywhere Python 3.10+ is present and can be distributed as a single downloadable executable script from GitHub Releases.

### 2. Built-in Deployment Profiles (`standard | preview | federation_head`)
* **Decision:** Offer 3 preset deployment profiles during setup:
  1. `standard` — Personal/family self-hosted node (`FEDERATION_ENABLED=true`, `FEDERATION_HEAD_MODE=false`).
  2. `preview` — Staging/preview node (`iqopresync` verification enabled).
  3. `federation_head` — Read-only Federation Hub (`FEDERATION_ENABLED=true`, `FEDERATION_HEAD_MODE=true`).
* **Rationale:** Directly supports setting up `iqoqo.cc` or peered community nodes with zero manual `.env` guesswork.

## Risks / Trade-offs

- **[Risk] Accidental overwrite of existing `.env` secrets** $\to$ **Mitigation:** Never overwrite existing non-empty `SECRET_KEY` or `POSTGRES_PASSWORD` values unless `--rotate-secrets` is explicitly passed alongside typed confirmation, and always write a timestamped `.env.bak.<ts>` backup with `0600` permissions.

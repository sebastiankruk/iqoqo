## 1. CLI Installer & `iqopresync` Verification (`scripts/` & `Makefile`)

- [x] 1.1 Implement `scripts/iqoqo_installer.py` (stdlib-only Python CLI) supporting interactive prompts and non-interactive flags (`--domain`, `--mode standard|preview|federation_head`, `--admin-email`, `--non-interactive`), 256-bit secret generation (`SECRET_KEY`, `JWT_SECRET_KEY`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD`), `0600` `.env` file permissions, and production overwrite confirmation guards.
- [x] 1.2 Implement `--presync-check` (`iqopresync`) mode in `scripts/iqoqo_installer.py` and add `make install-wizard` and `make presync-check` targets in `Makefile` to validate `.env` completeness, Docker/Compose status, `/api/health`, `/api/system/status`, and WebFinger/NodeInfo federation endpoints.
- [x] 1.3 Add CI packaging and checksum generation for the installer in `.github/workflows/` and document usage in `docs/INSTALL.md`.

## 2. Verification & Test Suite

- [x] 2.1 Author unit and BATS tests in `tests/scripts/test_iqoqo_installer.py` and `tests/bash/iqoqo_installer.bats` verifying `0600` `.env` generation, secret entropy, `federation_head` profile output, production overwrite guard, and `--presync-check` diagnostics.
- [x] 2.2 Run `IQOQO_AI_MODE=1 make lint` and `IQOQO_AI_MODE=1 make test-parallel`.

## Context

See `proposal.md` and `.context/notes/plan/Restore API keys - Google login after 1.0.2 upgrade.md`. Only four values differ between `.env` and `.env.prod`: `SECRET_KEY`, `JWT_SECRET_KEY`, `AUTH_SECRET`, `SECRET_KEY_LAST_ROTATED`. Secrets in `InstanceSettings` are Fernet-encrypted from `SECRET_KEY`; ciphertext is intact, only the wrong key was loaded.

## Goals / Non-Goals

**Goals:**

- Prebuilt targets resolve `${ENV_FILE:-.env}` to the same file passed via `--env-file`.
- Key drift is detected loudly by `make status` and at startup.
- Fail-closed behavior of `ConfigService.get()` stays covered by tests.

**Non-Goals:**

- Rotating keys, editing DB rows, changing images, or adding migrations.
- Logging or exposing secret values.

## Decisions

1. **Export, not only interpolate:** Makefile prebuilt `start` passes `ENV_FILE=$(COMPOSE_ENV_FILE)` to `docker compose pull` and `up -d`. Default behavior with `.env` is unchanged.
2. **Docs use the Make target:** `docs/INSTALL.md` shows `make prebuilt prod start`, or the explicit `ENV_FILE` plus `--env-file` pair.
3. **`APP_VERSION`:** `${APP_VERSION:-prod}` on `web` and `worker` so reported version matches the running image.
4. **Status guardrail:** `scripts/iqoqo-status.sh` decrypts one encrypted `InstanceSettings` row without printing it; on `InvalidToken` it fails with a hint naming `ENV_FILE` mismatch vs `make migrate-secrets`.
5. **Fail closed is kept:** Existing `ConfigService.get()` behavior (unset plus warning on `InvalidToken`) is asserted by a unit test, not altered.
6. **Phase 3 is gated:** Startup drift `ERROR` and the upgrade note are implemented only after the user confirms (note marks them "ask first").

## Risks / Trade-offs

- **[Risk] Makefile change alters deploy flows** -> Mitigation: `.env` default preserved; `tests/test_infra_config.py` asserts both cases.
- **[Risk] Status probe false alarm on fresh install with no encrypted rows** -> Mitigation: probe reports "no encrypted rows" as OK.

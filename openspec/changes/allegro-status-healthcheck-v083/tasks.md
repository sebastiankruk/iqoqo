## 1. Status Script & Probe Hardening

- [ ] 1.1 Update `scripts/iqoqo-status.sh` dev and prod/container probe blocks to initialize Flask application context via `create_app().app_context()`; verify probe output directly via bash execution
- [ ] 1.2 Refactor status categorization in `scripts/iqoqo-status.sh` to output `probe error` when `reason` is `query_failed` and `pass` when token is active or refreshable; verify output across simulated token states

## 2. Token Status Logic & Tests

- [ ] 2.1 Audit and refine `get_allegro_token_status` in `app/utils/allegro.py` to ensure robust error handling and return clean reason strings (`not_configured`, `handshake_pending`, `active`, `expired`, `probe_error`); verify with pytest in `tests/test_allegro_status.py`
- [ ] 2.2 Add automated bats tests in `tests/bash/status_check.bats` asserting correct Allegro status output for unconfigured, active, expired, and pending instances
- [ ] 2.3 Verify `make status` and `make status prod` locally and confirm no false warnings are displayed

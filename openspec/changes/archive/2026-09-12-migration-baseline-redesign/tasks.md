## 1. Migration DAG Redesign

- [x] 1.1 Create `migrations/versions/v0_7_17_baseline.py` representing canonical 0.7.17 state (`down_revision = None`) and remove `v0_7_18_baseline.py`
- [x] 1.2 Create `migrations/versions/v0_7_18_fixes.py` (`down_revision = 'v0_7_17_baseline'`) implementing `auth.token_blocklist.expires_at`, `config.instance_settings`, and 0.7.18 CheckConstraints
- [x] 1.3 Update migration bridge in `migrations/env.py` and `run.sh` to detect legacy head `f65648a6aaf4` and stamp `v0_7_17_baseline`

## 2. Scripts & Automation Cleanup

- [x] 2.1 Revert ad-hoc schema patches in `scripts/clone.sh` and update `scripts/fix_alembic.py` to map legacy heads to `v0_7_17_baseline`
- [x] 2.2 Update automated migration tests in `tests/test_migration.py` to verify DAG heads, bridge stamping, and clean upgrades

## 3. Verification & Live Preview Validation

- [x] 3.1 Run full migration and model test suites (`pytest tests/test_migration.py tests/test_models.py tests/test_ontology.py`) and verify all pass
- [x] 3.2 Run linters (`make format-python` and `make lint-python`) and verify zero errors
- [x] 3.3 Verify live preview deployment by running `docker compose exec web flask db upgrade` and testing login flow

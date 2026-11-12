# Tasks: Connected Server Footer, Batch-Scan State & Status Hygiene (`C120` — Target: `v1.0.3`)

## 1. Frontend

- [ ] 1.1 Show connected server host in the shared `Footer` (truncate with tooltip on small screens).
- [ ] 1.2 Add accessible batch-scan ON/OFF indicator to `/scan` with `aria-live`, default OFF.
- [ ] 1.3 Add `en.json`/`pl.json` strings for both.

## 2. Preview Restart (`iqoprerest`)

- [ ] 2.1 Locate the `iqoprerest` / `iqopretest.sh` script (not in this repo's tracked files) and decide whether to bring it under version control.
- [ ] 2.2 Replace the early health probe with a bounded readiness wait that hides transient errors and exits non-zero only on timeout.
- [ ] 2.3 Wait for OTel collector and OpenObserve readiness before running `make status`.

## 3. `make status` Hygiene (`scripts/iqoqo-status.sh`)

- [ ] 3.1 OTel export check: count failures only after the collector start grace window; keep `fail` for sustained failures.
- [ ] 3.2 Add the env classification file (`default`/`optional`/`required`) covering every `.env.example` key; review `DEPLOY_TOKEN`, `BASE_URL`, `FEDERATION_HEAD_MODE` against code reads.
- [ ] 3.3 Update the Environment Configuration section to print `required` gaps as warnings and the rest as info.
- [ ] 3.4 Make the `Recent 5xx errors` line consistent with its count and threshold.
- [ ] 3.5 Document the status categories briefly in `docs/`.

## 4. Tests

- [ ] 4.1 Vitest: footer host rendering; indicator default OFF, toggle ON, announcement.
- [ ] 4.2 BATS/pytest: classification covers every `.env.example` key; defaulted variable not a warning; required variable warns; OTel grace window vs sustained failure.
- [ ] 4.3 Verify with `IQOQO_AI_MODE=1 make lint` and `IQOQO_AI_MODE=1 make test-parallel`; add a `docs/CHANGELOG.md` entry.

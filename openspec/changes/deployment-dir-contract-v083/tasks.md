## 1. Validate the deployment directory

- [ ] 1.1 Add `scripts/validate_deploy_dir.py DIR`, exiting non-zero with an actionable message per violation. Checks, each naming the path and the remedy:
  - a runtime file (`scripts/`, `deploy/nginx.conf`, `shared/`, the ontology dir) that is a symlink resolving **outside** `DIR`;
  - a file-target mount source that is a directory;
  - a required compose file that is absent;
  - a required env file that is absent.
- [ ] 1.2 Report **all** violations in one pass, grouped by kind, rather than aborting on the first. An operator fixing a layout should see the whole list once.
- [ ] 1.3 Permit symlinks that resolve **within** `DIR` — sharing one directory between instances is legitimate and must not be flagged.
- [ ] 1.4 Add pytest coverage for each violation class, the intra-directory symlink case, and a clean directory.

## 2. Sync runtime files into the deployment directory

- [ ] 2.1 Add `scripts/sync_deploy_dir.py SRC_DIR DEPLOY_DIR`, copying the compose files, `scripts/`, `shared/`, `deploy/nginx.conf` and the ontology files as **real files**, replacing any existing symlink at those paths.
- [ ] 2.2 Print a manifest of synced paths with content hashes, so "what code is this deployment running" is answerable from the deploy log.
- [ ] 2.3 Make it idempotent and report `no changes` when sources are unchanged.
- [ ] 2.4 **Remove** files that a previous sync created and that no longer exist upstream. Stale runtime files are worse than missing ones: they execute silently.
- [ ] 2.5 Preserve file modes, and refuse to follow a symlink out of `SRC_DIR` while copying.
- [ ] 2.6 Add `make deploy-verify DIR=` that re-checks the manifest against the deployment directory and reports drift.

## 3. One env file per deployment

- [ ] 3.1 Introduce `DEPLOY_DIR ?= /opt/pre.iqoqo` in the `Makefile` as the single source of truth; keep `PREVIEW_DIR` working as an alias so existing invocations do not break.
- [ ] 3.2 Derive the env file from it (`$(DEPLOY_DIR)/.env`) instead of configuring `PREVIEW_ENV_FILE` independently.
- [ ] 3.3 Add `--deploy-dir` to `scripts/iqoqo-status.sh`, and have `make status` pass it. It must read that directory's env file and MUST NOT fall back to an env file in the working directory.
- [ ] 3.4 Point every other tool that reads deployment configuration — backups, archive, clone, cron — at the derived env file. Grep for `PREVIEW_ENV_FILE` and `IQOQO_ROOT/.env.<stack>` and remove the duplication.
- [ ] 3.5 Add a test that asserts the deploy path and the status path resolve the **same** env file for a given deployment directory. This is the regression that cost time during `rum-token-hardening`.

## 4. Pre-deploy mount validation

- [ ] 4.1 Add a pre-`compose up` step to the Makefile deploy path: for every bind-mount source, verify a file target is a file and create a missing directory source with the application user's ownership and an explicit mode.
- [ ] 4.2 Never remove or replace an existing directory where a file is expected — report and abort. Its contents may be real state.
- [ ] 4.3 Fix the live instance: `/opt/pre.iqoqo/.allegro_token.json` is an empty **root-owned directory** created by Docker's implicit behaviour. Determine whether the token file has content anywhere (it is Allegro auth state) before replacing it; if it is genuinely empty, replace the directory with a file.
- [ ] 4.4 Audit every `./`-relative mount in `docker-compose.yml` for the same latent outcome, and confirm each one is created by the pre-flight step rather than by Docker.
- [ ] 4.5 Extract the guard `run.sh` already carries for `.allegro_token.json` into the shared pre-flight, so both deploy paths use one implementation.

## 5. Share the existing guards

- [ ] 5.1 Apply secrets-file permission tightening (`0600`) on the Makefile deploy path, as `run.sh` does. `make preview-up` currently leaves `/opt/pre.iqoqo/.env` at whatever mode it had.
- [ ] 5.2 Confirm the RUM provisioning step added by `rum-token-hardening` runs on both deploy paths, and that the token reaches the frontend container on each.
- [ ] 5.3 Document the two deploy paths and state which guards each applies, so the next divergence is visible rather than latent.

## 6. Ontology validation must actually run

- [ ] 6.1 Resolve whether `scripts/sync_ontology.py` should receive the ontology files by mount or by build. It currently reads `/usr/src/app/docs/ontology/iqoqo.ttl`, which no mount provides, so it reports drift on every deploy and exits 0.
- [ ] 6.2 Make it distinguish "ontology source unavailable" from "ontology drift". A missing file is not drift and must not be reported as such.
- [ ] 6.3 Decide the failure mode for an unavailable source — gated warn-and-continue with an explicit acknowledgement, per design Decision 4 — and implement it. It MUST NOT exit 0 while appearing to have validated.
- [ ] 6.4 Confirm against the live preview deployment that the check runs against a real file and reports drift-free, so the `v0.8.0` ontology guarantee is actually in force.

## 7. Deployment directory maintenance

- [ ] 7.1 Add `make deploy-maintain DIR=` that reports debris — files no deploy step creates — naming each path, and removing nothing by default.
- [ ] 7.2 Prune `.env.bak.*` beyond a retention count, warning first that they contain secrets. These are derived state, regenerated by rotation.
- [ ] 7.3 Recognise data directories (covers, gallery, exports, uploads) and never offer to remove them.
- [ ] 7.4 Investigate the stray file `/opt/pre.iqoqo/1`, which holds captured `migration` container output, and find what created it. If a redirect typo exists in tracked tooling, fix it; if it was ad-hoc, record it as the kind of debris 7.1 exists to surface.

## 8. Migration of the live deployment directory

- [ ] 8.1 Back up `/opt/pre.iqoqo/.env` before touching anything, and record the current symlink set so the change is reversible.
- [ ] 8.2 Run the sync step, replacing the five symlinks with real files. Verify no symlink escaping the directory remains.
- [ ] 8.3 Re-point `make status preview` at the derived env file and confirm it reports the **actual** OpenObserve port and health. It currently reports `:5081` while the container listens on `:5080`.
- [ ] 8.4 Restart the stack and confirm every service is healthy, `/api/health` returns 200 through nginx, and RUM ingest still succeeds on the public origin.

## 9. Verification

- [ ] 9.1 bats: deploy into a temporary directory that has **no** sources and only an env file; assert `compose up` succeeds and the stack reports healthy without the operator creating anything by hand.
- [ ] 9.2 bats: the decisive self-containment test — deploy into a temporary directory, then **move the originating checkout away**, and assert the stack still serves traffic and reports healthy. This is the requirement that motivated the change.
- [ ] 9.3 bats: assert the validator rejects each violation class, and that an intra-directory symlink is accepted.
- [ ] 9.4 bats: assert the pre-flight creates a missing directory source as the application user, never as root.
- [ ] 9.5 Run `make lint-shell` and the full pytest suite. `tests/test_linting.py::test_shellcheck` skips when shellcheck is absent, so it must be installed locally.
- [ ] 9.6 Confirm on the live preview deployment that no symlink in the deployment directory resolves outside it, and that `make status preview` reports values the deployment actually started with.

## 10. Documentation

- [ ] 10.1 Add a `docs/DEPLOYMENT.md` (or an equivalent section in the install guide) describing the deployment-directory contract: required files, which are data, what must not be symlinked, and the deploy/sync/verify/maintain commands.
- [ ] 10.2 Document the two deploy paths and which guards each applies.
- [ ] 10.3 Document the OpenObserve root-password gotchas already recorded in `docs/MONITORING.md` — the strength policy and initialisation-only application — so they are found before a crash-loop rather than during one.
- [ ] 10.4 Cross-link from `docs/INSTALL.md` and the README so a new operator reaches the contract before their first deployment.
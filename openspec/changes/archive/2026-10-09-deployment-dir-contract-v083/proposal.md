## Why

A deployment directory — a directory that holds only the compose files, the env
file, and mounted **data**, with no application sources — is a legitimate way to
run iqoqo. It is what `make preview-up` deploys: `/opt/pre.iqoqo` has no
`migrations/`, no `tests/`, and only `app/static/` and `frontend/public/` from
the app tree. The proposal is to make that layout a supported, documented
contract rather than an accident that happens to work.

It does not currently work in a sound way. Everything below was found by
inspecting the live deployment while verifying `rum-token-hardening`, and every
item is a latent failure rather than a cosmetic one.

### 1. The deployment is not self-contained — it is a symlink farm

```
/opt/pre.iqoqo/Makefile                     -> /home/.../iqoqo/Makefile
/opt/pre.iqoqo/scripts                      -> /home/.../iqoqo/scripts
/opt/pre.iqoqo/deploy                       -> /home/.../iqoqo/deploy
/opt/pre.iqoqo/docker-compose*.yml          -> /home/.../iqoqo/docker-compose*.yml
```

`./scripts` is bind-mounted into **three** containers (`docker-compose.yml:54,
90,202`). So the running preview stack executes scripts straight out of a
developer working tree: editing a script file in the repo changes the code
running in the deployed containers without a redeploy, and checking out another
branch silently changes the deployment. Moving, renaming, or deleting that
checkout breaks a running deployment. A deployment directory that is not
independent of someone's laptop is not a deployment.

### 2. The env file a stack runs on is not the one the tooling reads

`make preview-up` deploys with `--env-file /opt/pre.iqoqo/.env`, but
`make status preview` resolves `ENV_FILE` to `$IQOQO_ROOT/.env.preview`
(`scripts/iqoqo-status.sh:90`). Two different files describe the same stack, so
diagnostics read values the deployment never used. This is not theoretical: it
made `make status` report OpenObserve on `:5081` while the container was on
`:5080`, which is precisely the misdirection that cost time during the
`rum-token-hardening` verification.

### 3. Two deploy paths with different guards

`./run.sh preview` and `make preview-up` deploy the same stack by different
routes. `run.sh` applies guards that the Makefile path does not:

- **`.allegro_token.json` is a directory, not a file.** `run.sh` has an explicit
  guard for this ("Docker creates missing bind-mount source paths as directories,
  which breaks container restarts for file-target mounts"). `make preview-up`
  has no such guard, and `/opt/pre.iqoqo/.allegro_token.json` is an empty
  root-owned directory created by exactly that failure.
- **Env permissions.** `run.sh` tightens secrets files to `0600`;
  `make preview-up` does not.

### 4. Bind mounts silently create root-owned directories

`./shared` is bind-mounted (`docker-compose.yml:55, 91, 202`) but absent from
the deployment directory, so Docker creates it — owned by root, invisible to the
operator's `git status` or `ls` habit, and not writable by the app user.
Anything absent is a candidate for the same outcome.

### 5. A file target the containers depend on is not mounted

The `migration` service runs `scripts/sync_db_permissions.py`, and
`scripts/sync_ontology.py` reads `/usr/src/app/docs/ontology/iqoqo.ttl`. There is
no `docs/` mount anywhere in `docker-compose.yml`, so the ontology check runs
against a missing file and reports drift on every deploy:

```
ERROR: Ontology syntax error (/usr/src/app/docs/ontology/iqoqo.ttl): File not found
✗ Drift or syntax errors detected between DB models and ontology.
```

It exits 0, so the failure is invisible — but it means the ontology validation
that `v0.8.0` was built around is not actually running in a deployed instance.
A deployment layout that silently disables a spec-level guarantee is worse than
one that fails loudly.

### 6. Deployment directories accumulate debris with no owner

`/opt/pre.iqoqo` also contains a stray file literally named `1` holding captured
container output from the migration service, and three `.env.bak.*` snapshots.
Nothing prunes or attributes them, so "is this file supposed to be here?" is
answerable only by a human.

## What Changes

- **Define the deployment-directory contract explicitly.** State exactly which
  files a deployment directory must contain, which are data (created if absent),
  and which must not be symlinks into a working tree. Add a validator that
  reports violations with actionable messages.
- **Make compose independent of a source checkout.** Everything the containers
  need at runtime — `scripts/`, `shared/`, `deploy/nginx.conf`, and the ontology
  files — is copied into the deployment directory at deploy time by a single
  sync step, instead of symlinked. The deployment directory becomes a real,
  self-contained artifact.
- **Make the env file singular.** One variable resolves the deployment
  directory; every target (`preview-up`, `preview-down`, `status`, backups,
  clone) derives its env file from it, so tooling and deployment cannot
  disagree about which `.env` describes a stack.
- **Share the guards across both deploy paths.** File-target mounts are
  verified to be files before `compose up`; secrets files are tightened; missing
  bind-mount sources are created with the right owner and mode rather than being
  silently created by Docker as root.
- **Fix the ontology validation gap** so a deployed instance actually runs it,
  rather than reporting phantom drift against a missing file.
- **Give deployment directories a lifecycle.** Attribute and prune debris, and
  document what may legitimately live there.

### Explicitly NOT changing

- **The bind-mount layout of `docker-compose.yml`.** Relocating application
  data (covers, gallery, exports, uploads) is out of scope; only the *runtime
  files* the containers execute or read are synced.
- **`run.sh`'s own dev-mode flow**, which runs from a checkout by design.
- **The `/api` surface and the FRBR ontology model.** Only the deployment of
  them changes.
- **Multi-stack host port divergence.** Different ports per deployment on one
  host are a supported feature, not a defect.

## Capabilities

### New Capabilities

- `deployment/deployment-dir-contract`: the required layout of a source-free
  deployment directory, the sync step that materialises runtime files into it,
  the single source of truth for its env file, the pre-deploy mount validation
  that prevents root-owned directories and file-target mounts, and the
  maintenance commands for its data and debris.

### Modified Capabilities

- `observability-health-validation`: `make status` currently resolves the env
  file independently of the deploy path, so it can describe a stack with values
  that stack never used. Diagnostics MUST read the env file of the deployment
  they are inspecting.

## Impact

- **Compose:** `scripts/`, `shared/`, `deploy/nginx.conf` and the ontology files
  become synced artifacts rather than symlinks; `docs/ontology` is mounted for
  the migration service.
- **Makefile:** `preview-up`/`preview-down` gain a pre-deploy validation and sync
  step; `status` gains deployment-directory awareness.
- **`scripts/`:** new deploy-sync and deploy-validate utilities, both runnable
  against any deployment directory.
- **Existing deployments:** `/opt/pre.iqoqo` must be re-synced once; the symlinks
  are replaced with real files. No data migration.
- **Tests:** validator coverage for each violation class, plus a bats test that
  deploys into a temporary directory with no sources and asserts the stack comes
  up and reports healthy.
## Context

`/opt/pre.iqoqo` is a working deployment directory that contains no application
sources. It was assembled by hand over time — `make clone` populates data into
it, and someone created symlinks so `docker compose` could find the compose
files. Nothing documents that, and nothing checks it, so the layout drifted into
a state where the running stack depends on a specific developer checkout.

This change makes that layout an explicit contract. It follows
`rum-token-hardening`, which surfaced most of the symptoms while verifying RUM
ingest on the live preview stack.

Two facts frame every decision:

1. **Compose resolves relative bind-mount paths against the project directory,
   not the compose file's directory.** With `--project-directory
   /opt/pre.iqoqo`, `./scripts` means `/opt/pre.iqoqo/scripts`. That is why the
   symlink farm works at all — and why an absent path becomes a root-owned
   directory rather than an error.
2. **`./scripts` is mounted into three containers.** Runtime code is therefore a
   first-class deployment artifact, not a build-time detail. Whatever ends up
   there is what runs.

## Goals / Non-Goals

**Goals:**

- A deployment directory is self-contained: moving, renaming, or deleting the
  originating checkout must not change a running deployment.
- Exactly one env file describes a deployment, and every tool resolves it the
  same way.
- A layout problem is a loud, actionable failure at deploy time, never a silent
  one at runtime.
- Guards that already exist in `run.sh` apply on the Makefile deploy path too.

**Non-Goals:**

- Moving application data. Covers, gallery, exports and uploads keep their
  current paths.
- Supporting deployments that intentionally run from a live checkout. `run.sh`
  dev mode already does that and will continue to.
- Multi-stack port divergence, which is a feature.

## Decisions

### Decision 1: Sync runtime files; never symlink them

**Decision:** a deploy step copies `scripts/`, `shared/`, `deploy/nginx.conf`
and `docs/ontology/` into the deployment directory as real files. A validator
rejects a deployment directory where any of them is a symlink pointing outside
it.

A symlink into a working tree makes the deployment a function of that tree's
current state — including which branch is checked out, and uncommitted edits,
which `run.sh` in another mode may be rewriting while the containers read it.
Copying also gives the deployment a reviewable, diffable manifest of exactly
which code it runs.

Symlinks *within* a deployment directory stay permitted: an operator may still
share one directory between instances deliberately.

**Alternatives considered:**
- *Bind-mount from the checkout by absolute path.* Rejected: it is the same
  coupling with less visibility.
- *Bake runtime files into the images.* Rejected as a much larger change;
  `shared/` and `deploy/nginx.conf` are legitimately edited per deployment, and
  the covers/gallery mounts already require host paths.

### Decision 2: One variable names the deployment directory, and it names the env file

**Decision:** `DEPLOY_DIR` (with `PREVIEW_DIR` as a compatibility alias) is the
single source of truth. The env file is `$(DEPLOY_DIR)/.env`, derived rather
than independently configured, and `iqoqo-status.sh` is given the same value.

`make status preview` and `make preview-up` disagreeing about the env file is
the single most expensive defect found during the previous change: it made the
diagnostics describe a stack that was not the one running. Deriving both from
one variable removes the possibility of disagreement rather than documenting the
convention.

A `--deploy-dir` flag on `iqoqo-status.sh` is required, since `make status` may
be invoked from a checkout that is not the deployment directory.

### Decision 3: Validate mounts before `compose up`, and create them ourselves

**Decision:** a pre-deploy check runs before every `compose up`. It:

- verifies each file-target mount source **is a file** (not a directory);
- creates each missing mount source directory with the app user's ownership and
  an explicit mode, instead of letting Docker create it as root;
- reports every violation in one pass rather than failing on the first.

Docker creating a missing source as a root-owned directory is how
`.allegro_token.json` became an empty root-owned directory. `run.sh` already
carries an explicit comment and guard for that one file; the general rule is
what is missing, and it belongs where both deploy paths can use it.

Creating directories is safe and idempotent. Replacing an existing *directory*
where a file is expected is not automatic — that case reports and aborts,
because the contents may be real state and the operator should decide.

### Decision 4: Ontology validation must run or say why

**Decision:** mount the ontology files the migration service reads, or pass the
path explicitly; and make the check's failure mode explicit.

Today `scripts/sync_ontology.py` reads a path that no mount provides, so it
reports drift on every deploy and exits 0. Two consequences, both bad: the
validation is decorative, and the "✓ drift-free" impression is false.

This change makes the check either run against a real file or report that the
ontology source is unavailable — and treats the latter as a failure the operator
must acknowledge, not a warning that scrolls past. The spec-level guarantee in
`ontology` capabilities depends on it.

### Decision 5: Deployment directories get a maintenance command

**Decision:** `make deploy-maintain DIR=…` reports and prunes debris, and prints
what it would remove before removing anything.

`/opt/pre.iqoqo` accumulated a stray file named `1` containing captured
container output, plus `.env.bak.*` snapshots with no owner. Two categories,
different risks:

- **Stray files** are either junk or state. Ambiguous by nature, so report first.
- **`.env.bak.*`** are provably derived state, regenerated by rotation, and may
  contain secrets. Prune beyond a retention count — after warning.

Anything ambiguous is reported, never deleted silently.

## Risks / Trade-offs

- **[Risk] Syncing copies code, so a deployment can drift from its checkout.**
  Mitigated by printing a manifest (path plus content hash) at sync time and by
  `make deploy-verify` re-checking it, so drift is detectable on demand. The
  alternative — silently following a working tree — is strictly worse.
- **[Risk] A deployment directory that legitimately shared files across instances
  would be rejected.** Mitigated by permitting intra-directory symlinks, so only
  escaping the directory is refused.
- **[Risk] Making the ontology check fatal could break existing deployments that
  have been passing on a missing file.** Accepted: it surfaces a real gap. It is
  gated to warn-and-continue with an explicit acknowledgement rather than a hard
  abort, so an operator can stage the fix.
- **[Trade-off] The sync step adds a deploy phase.** It is a file copy of a few
  hundred kilobytes, and it replaces a class of nondeterministic behaviour.
- **[Trade-off] Pre-deploy validation adds a failure mode to deploys.** It fails
  on states that are already broken, and reports all of them at once.

## Migration Plan

1. Add the validator and the sync step; both accept a target directory.
2. Run the sync against `/opt/pre.iqoqo`, replacing the symlinks with real files.
3. Repoint `status`, backups and clone at the derived env file.
4. Add the mount pre-flight to both deploy paths.
5. Fix the ontology mount; confirm the check runs against a real file.
6. Add `deploy-maintain` and `deploy-verify`.
7. End-to-end: deploy into a temporary directory with no sources, from a
   checkout that is then moved away, and assert the stack still serves traffic
   and reports healthy.

**No data migration.** Covers, gallery, exports and uploads are untouched. The
only irreversible step is replacing symlinks with copies, which is reversible by
recreating the symlinks, and is the point of the change.

## Open Questions

- Should `docs/ontology` be mounted read-only into the migration container, or
  copied into the image at build time? Read-only is simpler and keeps the
  ontology editable per deployment, which matches how `shared/` behaves today.
  Resolve during implementation with the migration service's actual reads.
- Does `run.sh prod` at `/opt/iqoqo` share this layout, or is preview the only
  deployment directory in use? The answer decides whether `DEPLOY_DIR` generalises
  or stays preview-scoped.
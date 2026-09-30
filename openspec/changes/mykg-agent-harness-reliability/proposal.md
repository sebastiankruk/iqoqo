## Why

`make mykg-update AI_AGENT=opencode` has been silently broken: it exits 0, reports "10/10 scopes updated", and produces **zero** LLM answers. Every task fails, and the failures are invisible because (a) the error was recorded as a bare exit code, (b) the daemon's exit status was discarded with `|| true`, and (c) a failed task is permanently marked done — so neither an incremental update nor a full reindex ever revisits it. The knowledge graph is quietly incomplete and no signal says so.

The root causes were three independent defects that masked each other, discovered by direct observation rather than by reading code:

1. **opencode v2 CLI drift.** `opencode run` dropped `--pure` and `--variant`; the variant is now a `provider/model#variant` suffix. Passing either made the CLI print usage and exit 1 on *every* task for *every* model.
2. **Credential not delivered.** opencode v2 no longer reads `auth.json` for provider credentials — it keeps them in the `credential` table of its own SQLite store, and the only CLI path to populate that (`opencode auth login`) refuses to run unattended for API-key providers. The sandbox mounted `auth.json` and nothing else, so it had no credential at all and every model reported `Model unavailable`.
3. **Queue abandoned on teardown.** The extraction runner is the producer and the daemon a consumer, but the `EXIT` trap removed the daemon as soon as the runner returned, stranding in-flight tasks with neither answer nor error — the worst possible outcome, because nothing reports it.

The pinned default model (`opencode/mimo-v2.5-free`) had also been retired from the provider registry, so the failure predated the v2 upgrade and had been masked as "wrong model".

## What Changes

- **BREAKING (internal CLI contract):** the opencode daemon invokes `opencode run --auto -m <provider/model#variant>`. `--pure` and `--variant` are removed. The reasoning effort maps to a variant suffix rather than a flag.
- **Variant selection becomes a degradation ladder.** Variant names are per-model and opencode v2 treats an unavailable variant as fatal. Effort now maps to an ordered preference list that always terminates at "no variant", and the daemon walks it on a `Variant unavailable` rejection instead of failing the task.
- **Credential delivery switches from file-staging to environment injection.** The read-only `auth.json` mount stays as the *source*; the daemon lifts the provider key out of it and passes it to the child process via the provider's declared environment variable. The key never appears on a command line, in a log line, or in `docker inspect`.
- **Failure detail is recorded.** Error envelopes carry the underlying CLI stderr, not just an exit code.
- **Transient failures become retryable.** A failed task carries an attempt count and is retried on later runs up to a bounded budget, instead of being terminal on first failure. A successful retry clears the stale failure record.
- **The agent queue is drained before teardown.** A bounded wait replaces the abrupt container removal, so in-flight tasks complete instead of being abandoned invisibly.
- **A sandboxed probe is added** (`make mykg-probe`) that exercises real model calls inside the real sandbox while never touching session state, with a host control run to separate "bad model name" from "broken harness".
- **A re-queue tool is added** (`make mykg-retry`) to clear failure markers for tasks that need another attempt, quarantining rather than deleting them so recovery is reversible.
- **Daemon start failures are fatal** instead of being swallowed by `|| true`.
- The default opencode model is repointed to a live registry entry, and a regression test asserts the default is actually present in `opencode models` output.

No user-facing API, schema, or FRBR ontology change.

## Capabilities

### New Capabilities
- `mykg-agent-queue-management`: lifecycle of the agent task queue — bounded drain before container teardown, re-queueing of failed tasks, and observability of queue depth, so that no task is ever lost without a record.

### Modified Capabilities
- `mykg-opencode-agent-harness`: the daemon's CLI invocation contract changes to opencode v2 (`#variant` suffix, no `--pure`/`--variant`), credential delivery changes from `auth.json` staging to environment injection, variant selection becomes a per-model degradation ladder, failures record CLI stderr, and a sandbox probe is added as the supported way to validate model availability without mutating pipeline state.
- `mykg-daemon-shared-core`: error envelopes gain an attempt count and stop being terminal on first write; `is_task_done` becomes budget-aware; a successful answer clears a stale error envelope. This directly changes the requirement that the first error wins.

## Impact

- `.agents/skills/iqoqo-mykg/scripts/opencode_daemon.py` — CLI construction, variant ladder, credential injection, error detail.
- `.agents/skills/iqoqo-mykg/scripts/daemon_core.py` — retry budget, `is_task_done`, error-envelope lifecycle.
- `.agents/skills/iqoqo-mykg/scripts/retry_failed.py` (new) — re-queue tool.
- `scripts/probe_opencode_harness.sh` (new) — sandboxed model probe.
- `scripts/mykg_sync.sh` — queue drain, fatal daemon-start failure.
- `Makefile` — `mykg-retry`, `mykg-probe`, live default model.
- `deploy/sandbox_proxy/allowlist-opencode.conf` — comment only; no new egress granted (a `models.dev` entry added during diagnosis was reverted as unjustified).
- `docker-compose.ai_sandbox.yml` — unchanged; the existing surgical `auth.json` mount is sufficient once the key is read from it.
- Tests: `tests/test_iqoqo_mykg.py`, `tests/bash/mykg_tooling.bats`.
- Operational: the opencode-go key must be present in `~/.local/share/opencode/auth.json`. Workspace privacy settings on opencode.ai can independently reject models that train on request data; that is a user-side setting, not a harness defect.

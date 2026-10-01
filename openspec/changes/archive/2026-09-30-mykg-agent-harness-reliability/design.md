## Context

See `proposal.md` — Why for motivation. What constrains the approach:

- **The opencode CLI is an unpinned external binary**, bind-mounted read-only from the host into the sandbox. Its CLI surface and credential model both changed between major versions, and nothing in the repo pins or asserts a compatible contract. This is the structural reason a whole class of breakage went unnoticed.
- **opencode v2 does not read `auth.json` for provider credentials.** They live in the `credential` table of its own SQLite store (`opencode.db`), populated only by `opencode auth login`, which refuses to run unattended for API-key providers. But the provider entry in the model catalogue declares an environment variable, so the key is reachable without the database.
- **The daemon and the extraction runner have different lifetimes.** The runner is a producer that returns when extraction finishes; the daemon is a consumer that may still be mid-flight. Teardown is driven by a shell `EXIT` trap.
- **The outbox is the only durable record of per-task outcome**, and both `update` and `index` consult the same per-task completion gate.
- **`mykg_sessions` is a symlink to shared storage**, so session discovery must follow symlinks.
- Session state is shared and long-lived; a large backlog of tasks can be pending at any time, and each one is a real billable model call.

## Goals / Non-Goals

**Goals:**
- Make model availability verifiable in the real sandbox without mutating pipeline state.
- Make a failed extraction recoverable without manual filesystem surgery, while bounding retries.
- Ensure no task is lost without a durable record, including the teardown-race case.
- Keep the credential out of process arguments, logs, and container inspect output.

**Non-Goals:**
- Pinning or vendoring the opencode CLI, or adding a compatibility shim across major versions. The harness tracks the installed binary's contract; a version gate is a separate concern.
- Automatic detection of a *missing* credential. Absence is reported as a warning; the CLI remains the source of truth for the resulting error.
- Changing the extraction pipeline, task payloads, or graph merge semantics.
- Working around opencode.ai workspace privacy settings, which independently reject some models.

## Decisions

### D1: Deliver the credential through the provider's declared environment variable

The daemon reads the provider key from the existing read-only `auth.json` mount and injects it into the child process environment, using a provider→env-var mapping sourced from the model catalogue entry (for `opencode-go`, `OPENCODE_API_KEY`).

**Why:** the database route is unavailable in an unattended container, and the compose file already mounts precisely the one file holding the key, so no new secret plumbing is needed.

**Alternatives considered:**
- *Mount the host `opencode.db`.* Rejected: it is multi-gigabyte, sqlite needs write access for `-wal`/`-shm`, and it contains the operator's full session and message history — an unacceptable disclosure into a sandbox that also mounts the repository.
- *Seed a minimal `opencode.db` with a single credential row.* Rejected: it depends on an undocumented internal schema that opencode migrates, so it breaks silently on upgrade.
- *Run `opencode auth login` at container start.* Rejected: it requires an interactive terminal for API-key providers.
- *Pass the key via compose `-e`.* Rejected: the value would be visible in `docker inspect` and in the container's environment listing.

An environment variable already present in the daemon's own environment takes precedence, so an operator can inject the key through compose without the mount.

### D7: Capture pipes with temp files, not `capture_output`

Both the daemon and the probe redirect the CLI's stdout/stderr to temporary files and pass `stdin=DEVNULL`.

**Why:** `opencode run` spawns `opencode serve --stdio`, which inherits the parent's stdout/stderr pipe write ends. If the client exits while the server lingers, the server still holds the write end, so a pipe-reading parent blocks forever waiting for EOF. The child it is waiting on has already exited, so the result is an indefinite hang with no live child to explain it.

**This was diagnosed from a process listing, not from a log.** During the investigation a hang was captured with the `opencode run` client absent from `/proc` while `serve --stdio` remained, reparented to pid 1 and spinning at 100% CPU. A live non-hung run showed all three processes. The daemon had always used temp files; the probe added during this work used `capture_output=True` and reintroduced the bug. So the most persistent symptom of this whole investigation was a regression in the diagnostic tool, not in the extraction path.

**Alternatives considered:**
- *Treat the spin as an opencode bug and only bound it with a timeout.* Rejected: it papers over a defect that is actually in how the CLI's output is captured, and a pipe-free parent is immune by construction.
- *Wait for a readiness signal from the server.* Rejected: the server is undocumented and its startup has no stable readiness contract.

### D8: Run the CLI in standalone mode

The daemon invokes `opencode run --standalone`, which uses a private `serve --stdio` server rather than connecting to the long-lived background service.

**Why:** the background service is a host-level process; inside a throwaway container there is none to connect to.

**Note on an earlier, incorrect claim:** this was initially recorded as removing an intermittent hang, on the basis of a process listing taken too early which appeared to show no server process. A later capture with correct timing showed `serve --stdio` is spawned in standalone mode too. The flag is kept because private-per-invocation is the correct behaviour in a container, not because it was shown to fix a hang.

### D9: Persist the opencode runtime store

The agent container mounts a named volume at `$HOME/.local`, holding opencode's SQLite database, logs, cache and XDG state.

**Why:** `$HOME` is an ephemeral tmpfs, so every task began from an empty store and re-ran the full 48-migration database schema bootstrap. The store now bootstraps once and is then reused.

**Status: unproven as a hang fix.** It was adopted on the theory that a per-task bootstrap was the risk, and it does remove that work, but the hang was ultimately attributed to pipe inheritance (D7) and this change was never shown to affect the failure. It is kept because eliminating 48 migrations per task is worthwhile on its own. It stores no credentials; `auth.json` remains on the read-only secret mount.

**Operational note:** the volume is created root-owned while the container runs as uid 1000, and opencode writes both `.local/share` and `.local/state`, so the mount must cover `.local` and the volume must be chowned to 1000:1000. Both mistakes produced `EACCES` during rollout.

### D10: Wait for egress-proxy health in the probe

The probe polls the proxy container's real health status before dispatching.

**Why:** the probe starts the agent with `--no-deps`, which bypasses compose's `depends_on: service_healthy` gate, and it previously relied on a fixed sleep. Because the probe stops the proxy on exit, a cold start was raced on most runs. `mykg_sync.sh` is unaffected: it starts the daemon without `--no-deps` and compose waits for it.

### D2: Variant selection as a terminating degradation ladder

Effort maps to an ordered preference list that always ends at "no variant". The daemon walks it only on a `Variant unavailable` rejection.

**Why:** variant names are published per model and opencode v2 treats an unavailable variant as fatal, so any single fixed mapping breaks whenever the model set shifts. Terminating at "no variant" is safe because every model accepts its default.

**Alternative considered:** a hardcoded effort→variant map (the previous behaviour). Rejected — it is exactly what broke, because `minimal` does not exist for the model that was pinned.

### D3: Bounded retry budget recorded in the error envelope

Error envelopes carry an `attempts` field. The completion gate treats a failure as terminal only once the count reaches a configurable budget (default 3). Writing increments; a successful answer deletes the envelope.

**Why:** extraction failures are overwhelmingly transient. The previous first-error-wins contract converted a single blip into permanent, invisible data loss. The cap is what keeps this safe — without it, a permanently broken model would be retried forever.

Legacy envelopes with no `attempts` field count as one attempt, so pre-existing failures benefit rather than being stranded.

**Alternative considered:** retry indefinitely. Rejected — unbounded retries against a misconfigured model is a resource-exhaustion path. **Also considered:** age-based expiry instead of a count. Rejected — a count is deterministic, testable without clock control, and independent of how often runs happen.

### D4: Bounded drain before teardown

After the producer returns, the sync script waits for unfinished tasks to reach zero before the `EXIT` trap removes the daemon.

**Why:** the teardown race strands tasks with neither answer nor error — the only outcome no consumer can detect. A bounded wait converts a silent loss into either completion or a reported backlog.

**Trade-off:** a run can now take longer, and a slow or stuck model will hold the container until the timeout. The wait is skippable, bounded, and reports progress, so the cost is bounded and visible. Teardown that races a consumer was the defect, not a necessary property.

**Two corrections learned from measurement, not from the first implementation:**

- A repeated *outstanding count* is not progress reporting. A drain that printed the same number every 60s looked identical whether the queue was draining or wedged, and it was in fact wedged. The drain now reports completions since the start and states plainly when nothing has completed within a reporting interval.
- Bounded waiting is not sufficient on its own. With a single worker, one slow task holds the queue for up to its own `timeout_seconds` — 1800s in practice, longer than a default drain window — so the drain can time out while merely waiting on one task. Concurrency above one is part of the fix, not a tuning nicety. Measured on this repository's real backlog: a single 116KB task takes ~13s, one worker sustains ~4 tasks/100s, two workers sustain ~17/180s.

### D5: Probe runs the daemon's own credential path

The probe imports the daemon module inside the sandbox and calls its environment builder, rather than constructing its own.

**Why:** the first version of the probe built its own environment and reported a false failure after the credential fix landed — precisely the drift this decision prevents. Making the probe depend on production code means it cannot diverge.

### D6: Host control run before sandboxed runs

The probe attempts the first model outside the sandbox first.

**Why:** "model unavailable" is ambiguous between a bad model name, a bad credential, and a broken environment. A passing control collapses the diagnosis to the environment in one command, and would have avoided a long, wrong investigation during this work.

## Risks / Trade-offs

- **The opencode CLI can change its contract again, and the harness tracks it implicitly.** → The probe is the detection mechanism, and it is cheap and state-free, so a future break is a 30-second check rather than a debugging session. A pin-and-gate is deliberately out of scope but is the natural follow-up.
- **A default effort whose variant is unavailable adds one wasted subprocess call per task before degrading.** → Mitigation: the ladder starts with the most likely variant, and the resolved variant is the first entry, so well-chosen efforts pay nothing.
- **A retry budget means a permanently failing task is attempted `MAX_TASK_ATTEMPTS` times across runs.** → Bounded by construction, and the count is visible in the envelope for diagnosis.
- **The drain extends wall-clock time and holds a container.** → Bounded by a configurable timeout, progress is reported, the wait is skippable, and timeout is not treated as a run failure.
- **The probe makes real billable model calls.** → Documented in its output; intended for deliberate use, not for automated invocation.
- **Sandboxed models can still be rejected for reasons outside the harness**, e.g. workspace privacy settings rejecting models that train on request data. → The probe reports the upstream message verbatim so these are distinguishable from harness faults.
- **Session state lives behind a symlink to shared storage**, so concurrent runs on the same session can race on the same envelopes. → Pre-existing condition; the atomic rename pattern limits corruption but does not eliminate the race. Not addressed here.

## Migration Plan

1. Ship the harness and credential changes together — the CLI contract change is inert without the credential delivery, and vice versa.
2. Run `make mykg-probe` to confirm the sandbox resolves models before touching pipeline state.
3. Existing failure envelopes are treated as one attempt, so the first run after deployment retries them automatically. Confirm progress via `make mykg-retry ARGS="--dry-run"`.
4. Rollback: revert the commit. Failure envelopes written with an `attempts` field remain readable by the previous code path as ordinary markers, so rollback degrades to the old terminal-marker behaviour rather than losing data.

## Open Questions

- Should the retry budget differ per failure class? A malformed task payload is not worth three attempts, whereas a timeout is. Deferred: the current envelope records a sanitized one-line reason, so classifying on it is possible later without changing the spec.
- Should the drain also apply to full reindex, where the inbox is the whole session tree? Deferred: `index` re-derives all tasks, so the stranded-task window is smaller, and the current drain is scoped to `update`.

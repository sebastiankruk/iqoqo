## 1. opencode v2 CLI Contract

- [x] 1.1 Remove the purity and standalone-variant flags from the daemon's CLI invocation and verify no argument list contains them (`grep -E '"--pure"|"--variant"'` returns nothing)
- [x] 1.2 Render the model identifier with the variant as a `#` suffix, replacing rather than duplicating an already-present variant, and verify via unit test
- [x] 1.3 Add a bats guard asserting the daemon never passes v1-only flags, so the regression cannot silently return
- [x] 1.4 Invoke the CLI with `--standalone` so no background `serve --service` process is spawned, eliminating the intermittent 100%-CPU spin that hung tasks until their timeout
- [x] 1.5 Add a regression test asserting `--standalone` is always passed and no server process is spawned
- [x] 1.6 Capture CLI stdout/stderr via temp files in the probe, never `capture_output=True`: a lingering `serve --stdio` keeps the inherited pipe write end open and blocks the parent on EOF forever after the client has exited
- [x] 1.7 Persist opencode's runtime store so the 48-migration database schema bootstrap runs once rather than per task (unproven as a hang fix; kept for the per-task cost)
- [x] 1.8 Wait for egress-proxy health in the probe, which starts the agent with `--no-deps` and therefore bypasses compose's `service_healthy` gate
- [x] 1.9 Make the probe capture hang diagnostics from inside the container, since `compose run --rm` removes the only evidence

## 2. Per-Model Variant Degradation

- [x] 2.1 Replace the fixed effort→variant map with ordered preference lists that always terminate at "no variant", and verify each ladder's last entry is the empty variant
- [x] 2.2 Walk the ladder on a variant-unavailable rejection only, and verify an unrelated failure is attempted exactly once
- [x] 2.3 Verify degradation against the live CLI: an effort whose variant the model does not publish falls through to a supported variant and returns a real answer

## 3. Credential Delivery

- [x] 3.1 Map providers to their catalogue-declared environment variable and read the key from the read-only auth mount, and verify the key never appears in the argument vector
- [x] 3.2 Inject the key into the child process environment, and verify the child receives it
- [x] 3.3 Let a pre-set environment variable take precedence over the mount, and verify precedence
- [x] 3.4 Tolerate an absent or malformed secret without fabricating a key or raising, and verify no crash
- [x] 3.5 Correct the credential-bootstrap docstring, which asserted that staging the file was sufficient, and verify the warning names the real consequence
- [x] 3.6 Verify end-to-end in the real sandbox: a model returns a real answer and the call is visible on the provider side

## 4. Diagnosable Failures

- [x] 4.1 Record the CLI's underlying error text in the failure envelope alongside the exit code, and verify the cause is readable from pipeline state alone
- [x] 4.4 **Regression fix (2026-09-30).** 4.1 was only satisfied on the *subprocess* path (`opencode_daemon.py:462`, which quotes the CLI's stderr — hence envelopes reading `getaddrinfo ETIMEOUT sandbox-egress-proxy`). The generic `except Exception` handler in both harnesses recorded only `type(exc).__name__`, so an envelope said just `Unexpected error: ValueError`, which identifies nothing. Six tasks from the 2026-09-30 run burned the full retry budget in exactly that state; the real cause (`Expecting ',' delimiter: line 1 column 13`) was only recoverable by grepping the 9 MB `run.log`, which is precisely what 4.1 forbids. Added `describe_unexpected_error()` to the shared core — it keeps the exception message, and for a bare `ValueError` (the common `json.loads` case, where `str()` is empty) reports the deepest traceback frame as `file.py:line in func()` instead. Wired into `opencode_daemon.py:328` and `agy_daemon.py:143` (the defect was copy-pasted into both). Redaction is unaffected: the message passes through the existing `sanitize_error_text()` on write, verified by a test asserting `/home/appuser` and `sk-abc` are still stripped. 5 tests added to `tests/test_iqoqo_mykg.py`, including a parametrized end-to-end check across both harnesses; confirmed to fail against the pre-fix behaviour.
- [x] 4.5 **NUL byte fix (2026-09-30) — the root cause 4.4 made visible.** Once the cause was legible, all six stuck tasks read `ValueError: embedded null byte`. Both harnesses pass the prompt as a **command-line argument**, and `subprocess.run()` raises before the CLI is ever contacted, so a single `0x00` anywhere in the indexed source fails the task irrecoverably — the retry budget cannot help, because the input does not change between attempts. The failing prompt carried exactly one NUL at offset 86,860. The NUL was **self-inflicted**: the graph had indexed an earlier run's own `ps` output, which contains the shell idiom `tr "\0" " " < $d/cmdline`, so one run's diagnostic output became the next run's poisoned input. `build_combined_prompt()` now drops NUL bytes — a terminator with no meaning in natural language, so lossless for the model — and **logs the count to stderr** rather than stripping silently, so the condition stays visible. 2 tests added, one of which asserts the built prompt is actually accepted by a live `subprocess.run()`. Verified against the real failing task file. **Confirmed effective in production:** the re-queued six went from 6 failed to 6 answered, with the strip warning firing exactly 6 times (see 9.2).
- [x] 4.2 Make daemon start failures fatal instead of discarding the status, and verify a failed start is reported with a log-inspection hint
- [x] 4.3 Repoint the default opencode model to a live registry entry, and verify with a test that asserts the default actually appears in the provider's model list

## 5. Retry Budget

- [x] 5.1 Record an attempt count in error envelopes, incrementing while budget remains and freezing the terminal envelope once spent
- [x] 5.2 Make the completion gate budget-aware so a transient failure is not terminal, while a real answer always wins
- [x] 5.3 Treat legacy envelopes without an attempt count as a single attempt, so pre-existing failures are not stranded
- [x] 5.4 Expose the budget as a configurable value and verify the gate honours an override
- [x] 5.5 Remove a stale failure marker when a task is subsequently answered, and verify a recovered task no longer advertises failure

## 6. Queue Drain

- [x] 6.1 Wait for unfinished tasks to reach zero before the teardown trap removes the daemon, verifying the wait is skipped when no daemon is running
- [x] 6.2 Bound the wait with a configurable timeout and treat timeout as a reported backlog rather than a failed run
- [x] 6.3 Report completions alongside the outstanding count, and warn explicitly when no task completes within a reporting interval, since an unchanged pending count is otherwise indistinguishable from a stall
- [x] 6.4 Raise daemon concurrency above one so a single slow task cannot block the queue, and verify throughput improves rather than assuming it
- [x] 6.5 Verify the drain end-to-end against a real backlog and confirm the pending-task count reaches zero, rather than plateauing. **Verified 2026-09-30 against a real 2,728-task backlog.** Final state: 2728 done, 0 failed, 0 pending — the count reached zero rather than plateauing, and the `DONE pass2` line confirms the orchestrator completed the 1-file/2-batch re-extraction that the re-queued tasks belonged to.

## 7. Operator Tools

- [x] 7.1 Add a re-queue target that clears failure markers for tasks that can actually be retried, quarantining rather than deleting them, and verify reversibility
- [x] 7.2 Classify failures before acting: leave markers on already-answered and payload-less tasks, and verify both are reported separately
- [x] 7.3 Support inspection mode and a named session, and verify a bogus session name does not silently fall back to the latest
- [x] 7.4 Follow a symlinked session store, and verify a symlink to shared storage is enumerated while a missing session is reported
- [x] 7.5 Add a sandboxed probe that exercises real model calls without touching session state, and verify outbox error counts are unchanged across a probe run
- [x] 7.6 Have the probe use the daemon's own credential path, and verify it cannot drift from production behaviour
- [x] 7.7 Add a host control run to the probe so a failure is attributable to the environment rather than the model
- [x] 7.8 Add a bats guard asserting the probe never references session inbox or outbox paths or the extraction runner

## 8. Egress Allowlist

- [x] 8.1 Revert the `models.dev` egress rule added during diagnosis and verify the opencode allowlist grants no unjustified egress
- [x] 8.2 Document in the allowlist why `models.dev` is deliberately absent, given the catalogue is served from the permitted host

## 9. Integration and Release

- [x] 9.1 Drain the outstanding task backlog with the drain in place and confirm pending tasks reach zero with no new failure envelopes. **Verified 2026-09-30.** Before: 2710 in the inbox, 2704 done, 6 failed, 0 pending. After: 2728 total, 2728 done, **0 failed, 0 pending** — the drain reached zero and produced no new failure envelopes.
- [x] 9.2 Confirm the previously re-queued failures are now answered rather than re-failed, and record the before/after counts. **Verified 2026-09-30. Before: 6 failed. After: 0 failed, 6 answered.** All six carry a real `.answer.json` and a `.done` marker. This task is what exposed the NUL defect, and is the evidence for it:

  | Task | Before (20:32) | After (21:12) |
  |------|----------------|---------------|
  | `29a682950d67` | `ValueError: embedded null byte` | answered |
  | `2f459fd600b4` | `ValueError: embedded null byte` | answered |
  | `659931b0ccce` | `ValueError: embedded null byte` | answered |
  | `663642e1f34e` | `ValueError: embedded null byte` | answered |
  | `9b053aebca24` | `ValueError: embedded null byte` | answered |
  | `e0dc8287a0e8` | `ValueError: embedded null byte` | answered |

  The NUL strip warning fired exactly 6 times in the daemon log, one per task, confirming the fix is what unblocked them. The NUL was **self-inflicted**: the graph had indexed an earlier run's own `ps` output, which contains a `tr "\0" " " < $d/cmdline` shell idiom — so a previous run's diagnostic output became the input that broke the next run.

  The 7th envelope, `4871e495` (`Subprocess failed with exit code 1: > build · space-bunny-free`), is correctly classified as **already answered** and left alone by `retry_failed.py`. Its retry budget was never spent and it needs no action.
- [x] 9.3 Run the full backend suite and the shell suite, confirming no new failures beyond known pre-existing ones. **Backend: 2375 passed, 3 skipped, 0 failed** (10m17s). **Shell: 276 ok, 2 not ok — both confirmed pre-existing and environmental, neither caused by this change:**
  - `#184 Makefile mykg-update preserves agy defaults when AI_AGENT=agy` — the test runs bare `make -n mykg-update` without setting `AI_AGENT`, so it inherits `AI_AGENT=opencode` from the operator's shell and asserts the agy default `gemini-3.8-flash-low` against an opencode-resolved recipe. Reproduced on the **base commit `2a9f550`** in a clean worktree, where it fails identically; passes with `env -u AI_AGENT`. The Makefile's agy default is correct (`Makefile:210,213`); the test is under-specified.
  - `#177 mykg query produces valid ontological output via make mykg-ask` — requires `output/nodes.jsonl`, which the current session lacks. Skips in a clean checkout (no `mykg_sessions/`) and fails here only because a live session exists in an incomplete state. This change touches no graph or query code.
- [x] 9.4 Add a changelog entry covering the v2 CLI contract, credential delivery, retry budget, queue drain, and the two new targets
- [x] 9.5 Commit the change set, since an earlier session lost uncommitted work to a stash operation. **Committed 2026-09-30 on `chore/0.8.2/moderate-findings-sweep` (3 commits: the diagnosability fix, the NUL fix, the OpenSpec archival).** The pre-existing `stash@{0}` from 2026-09-30 04:21 was audited: every symbol it contains is already present in `HEAD` (it is the pre-merge state of PR #319, which is an ancestor here), so nothing is lost by leaving it. **It has been left in place** rather than dropped, since removing a stash is not reversible from the reflog alone.

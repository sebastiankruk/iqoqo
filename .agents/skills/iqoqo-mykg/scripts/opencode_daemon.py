#!/usr/bin/env python3
# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>
#
"""Autonomous background daemon for processing myKG agent inbox tasks via opencode CLI.

This module implements the opencode-specific CLI adapter. All shared logic (task
discovery, payload sanitization, security guardrail injection, JSON fence
stripping, timeout negotiation, answer-envelope writing, signal handling,
worker-pool dispatch) is imported from daemon_core.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Import shared core from the same directory
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from daemon_core import (  # noqa: E402
    REDACTED_PATTERNS,
    SECURITY_GUARDRAIL,
    build_combined_prompt,
    clean_json_fences,
    compute_effective_timeout,
    describe_unexpected_error,
    discover_tasks,
    is_task_done,
    load_and_validate_task,
    sanitize_task_payload,
    write_answer_envelope,
    write_error_envelope,
)
from daemon_core import (
    run_daemon as _run_daemon_core,
)

# Re-export shared symbols for backward-compatible test access
__all__ = [
    "REDACTED_PATTERNS",
    "SECURITY_GUARDRAIL",
    "bootstrap_opencode_auth",
    "build_combined_prompt",
    "build_subprocess_env",
    "clean_json_fences",
    "compute_effective_timeout",
    "discover_tasks",
    "is_task_done",
    "load_and_validate_task",
    "map_effort_to_variant",
    "process_task",
    "read_provider_api_key",
    "variant_candidates",
    "run_daemon",
    "sanitize_task_payload",
    "write_answer_envelope",
]


# Reasoning-effort ladder for opencode v2.
#
# opencode v2 dropped `--pure` and `--variant` from `opencode run`; the variant
# is now a `#suffix` on the model string (`provider/model#variant`). Variant
# names are per-model and v2 exits non-zero with "Variant unavailable for
# <model>: <variant>" when a model does not publish the requested one, so a
# single hardcoded mapping breaks as soon as the model set shifts.
#
# Each entry is an ordered preference list, most-specific first, always ending
# in None. None means "send no variant", which every model accepts. The daemon
# walks this list on a "Variant unavailable" failure, so an unknown model
# degrades to the default variant instead of failing every task.
EFFORT_VARIANT_LADDER: dict[str, tuple[str | None, ...]] = {
    "minimal": ("minimal", "low", None),
    "low": ("low", "minimal", None),
    "medium": ("medium", "low", None),
    "high": ("high", "xhigh", "max", "medium", None),
}


def variant_candidates(effort: str | None) -> tuple[str | None, ...]:
    """Return the ordered variant preference list for an effort level."""
    return EFFORT_VARIANT_LADDER.get((effort or "").lower(), (None,))


def map_effort_to_variant(effort: str) -> str | None:
    """Map an agy-style effort level to its preferred opencode v2 variant.

    Returns None when the effort is unknown or maps to the default variant.
    This is the first entry of variant_candidates(); the daemon uses the full
    ladder, this stays for callers that only need a single answer.
    """
    return variant_candidates(effort)[0]


def build_model_spec(model: str, variant: str | None) -> str:
    """Render the `provider/model[#variant]` string opencode v2 expects."""
    base = model.split("#", 1)[0].strip()
    if not variant:
        return base
    return f"{base}#{variant}"


def is_variant_unavailable(stderr_data: str) -> bool:
    """Detect opencode's "Variant unavailable" rejection in stderr."""
    return "variant unavailable" in (stderr_data or "").lower()


# Where the opencode-go API key is read from. The compose file bind-mounts the
# host's auth.json here (read-only, single file) so the sandbox never needs the
# whole credential store.
# Last-resort model when neither the argument nor the environment names one.
# Must be free-tier: a missing env var should not silently start spending the
# operator's inference budget. Keep this in sync with OPENCODE_DEFAULT_MODEL
# in the Makefile.
DEFAULT_MODEL = "opencode-go/space-bunny-free"

# Wall-clock ceiling for a single `opencode run` invocation, in seconds. See the
# comment at the call site for why this is far below the task's own timeout.
MAX_CLI_TIMEOUT = int(os.environ.get("MYKG_MAX_CLI_TIMEOUT", "300"))

AUTH_SECRET_PATH = Path("/run/secrets/opencode-auth.json")

# Provider id -> environment variable holding its API key. Taken from the
# provider entry in the models.dev catalogue, e.g. opencode-go declares
# {"env": ["OPENCODE_API_KEY"], "api": "https://opencode.ai/zen/go/v1"}.
PROVIDER_ENV_VARS = {
    "opencode-go": "OPENCODE_API_KEY",
    "opencode": "OPENCODE_API_KEY",
}


def read_provider_api_key(model: str | None = None) -> str | None:
    """Read the API key for a provider out of the mounted auth.json.

    opencode v2 stopped reading auth.json for provider credentials. It keeps
    them in the `credential` table of its own SQLite store (opencode.db), which
    is populated by `opencode auth login` — and that command demands an
    interactive terminal for API-key providers, so it cannot run unattended in
    the daemon. Instead the provider takes its key straight from the
    environment, per its catalogue entry.

    Without this, every task fails with "Model unavailable: <provider>", because
    the sandbox has no credential at all.
    """
    provider = (model or "").split("/", 1)[0].strip() or "opencode-go"
    env_var = PROVIDER_ENV_VARS.get(provider)
    if env_var is None:
        return None

    # An explicit env var (e.g. injected by compose) always wins.
    existing = os.environ.get(env_var)
    if existing:
        return existing

    candidates = [AUTH_SECRET_PATH]
    home = Path(os.environ.get("HOME", "/home/appuser"))
    candidates.append(home / ".local" / "share" / "opencode" / "auth.json")

    for candidate in candidates:
        try:
            if not candidate.is_file():
                continue
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        entry = payload.get(provider)
        if isinstance(entry, dict):
            key = entry.get("key")
            if isinstance(key, str) and key:
                return key

    return None


SMALL_MODEL = os.environ.get("MYKG_OPENCODE_SMALL_MODEL", DEFAULT_MODEL)


def write_opencode_small_model_config(model: str | None = None) -> None:
    """Pin opencode's auxiliary ("small") model so it cannot pick its own default.

    opencode routes internal work -- session title generation and, when context
    fills, auto-compaction -- to a `small_model` from its config. When that key
    is absent, opencode chooses one itself, and its choice is a paid model
    (gpt-6-luna) served over a different protocol (/responses) than the
    extraction model. That produced two consequences: unbilled-by-us auxiliary
    traffic to a model the operator had deliberately blocked, and an extra
    network round trip per task that could fail or stall independently of the
    extraction call itself.

    The daemon container mounts no opencode config, so this writes one at
    startup next to the staged auth.json. There is no OPENCODE_SMALL_MODEL env
    var, so the config file is the only supported route.
    """
    home = Path(os.environ.get("HOME", "/home/appuser"))
    target_dir = home / ".config" / "opencode"
    target = target_dir / "opencode.json"
    spec = build_model_spec(model or DEFAULT_MODEL, None)

    payload = {"small_model": spec}
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except OSError as err:
        # Non-fatal: without it opencode just falls back to its own default.
        print(
            f"[opencode_daemon] Warning: could not pin small_model to {spec}: {err}",
            file=sys.stderr,
            flush=True,
        )


def build_subprocess_env(model: str | None = None) -> dict[str, str]:
    """Build the environment for the opencode child process.

    SECURITY: the key is read from the read-only secret mount at call time and
    passed only in the child's environment. It is never written to a log line,
    a command line, or a file inside the container.
    """
    env = os.environ.copy()
    key = read_provider_api_key(model)
    provider = (model or "").split("/", 1)[0].strip() or "opencode-go"
    env_var = PROVIDER_ENV_VARS.get(provider, "OPENCODE_API_KEY")
    if key:
        env[env_var] = key
    return env


def bootstrap_opencode_auth() -> None:
    """Stage the surgically-mounted auth secret and pin the auxiliary model.

    NOTE: this copy alone is NOT sufficient for opencode v2. v2 no longer reads
    auth.json for provider credentials — it keeps them in the `credential` table
    of its own SQLite store, and the only CLI path to populate that
    (`opencode auth login`) refuses to run unattended for API-key providers.
    The key actually reaches the model through OPENCODE_API_KEY, set per-child
    in build_subprocess_env(). The copy is kept because it is cheap, preserves
    the 0o600 permissions, and keeps the home self-describing for anything
    else that inspects the credential store.

    SECURITY: Credentials are copied from the Docker secrets mount to user home
    because the CLI tools expect them in specific paths. We use 0o600
    permissions and never log the credential content. The secret mount is
    read-only and isolated by the container runtime.
    """
    secret_path = AUTH_SECRET_PATH
    home = Path(os.environ.get("HOME", "/home/appuser"))
    target_path = home / ".local" / "share" / "opencode" / "auth.json"

    if not secret_path.is_file():
        print(
            "[opencode_daemon] Warning: secret mount /run/secrets/opencode-auth.json not found. "
            "The opencode-go key will not be available, so every task will fail "
            "with 'Model unavailable: <provider>'.",
            file=sys.stderr,
        )
        return

    if target_path.exists():
        return

    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(secret_path.read_bytes())
        os.chmod(target_path, 0o600)
    except OSError as err:
        print(f"[opencode_daemon] Warning: failed to copy auth.json: {err}", file=sys.stderr)


def process_task(
    task_path: Path,
    outbox_dir: Path,
    model: str | None = None,
    effort: str | None = None,
    max_retries: int = 3,
) -> bool:
    """Process a single task file by calling opencode and writing the answer atomically.

    SECURITY: Uses compute_effective_timeout() which honors the task's
    timeout_seconds field and applies a hard cap (MAX_TIMEOUT_CAP) to
    prevent resource exhaustion from malicious or buggy orchestrator payloads.
    """
    task_id = task_path.stem.split(".")[0]

    if is_task_done(task_id, outbox_dir):
        return True

    for attempt in range(max_retries):
        try:
            return _execute_task(task_path, outbox_dir, model, effort, attempt)
        except subprocess.TimeoutExpired:
            if attempt < max_retries - 1:
                wait_time = 2**attempt  # Exponential backoff: 1s, 2s, 4s
                print(
                    f"[opencode_daemon] TimeoutExpired for task {task_id}, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})",
                    file=sys.stderr,
                    flush=True,
                )
                time.sleep(wait_time)
            else:
                write_error_envelope(task_id, "Subprocess timed out after all retries", outbox_dir)
                print(
                    f"[opencode_daemon] TimeoutExpired for task {task_id} after {max_retries} attempts",
                    file=sys.stderr,
                    flush=True,
                )
                return False
        except Exception as exc:  # pylint: disable=broad-exception-caught
            detail = describe_unexpected_error(exc)
            write_error_envelope(task_id, f"Unexpected error: {detail}", outbox_dir)
            print(f"[opencode_daemon] Error processing task {task_id}: {detail}", file=sys.stderr, flush=True)
            return False

    return False


def _run_opencode(cmd: list[str], effective_timeout: int, model: str | None = None) -> tuple[int, str, str]:
    """Run the opencode CLI, returning (returncode, stdout, stderr).

    SECURITY: stdout/stderr go to temp files rather than pipes. opencode's
    internal IPC/event-bus writes to stdout immediately after the 'init'
    handshake, so capture_output=True fills the pipe buffer and deadlocks
    before the process can exit.
    """
    with (
        tempfile.TemporaryFile(mode="w+", encoding="utf-8", suffix=".stdout") as stdout_f,
        tempfile.TemporaryFile(mode="w+", encoding="utf-8", suffix=".stderr") as stderr_f,
    ):
        proc = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,  # prevent opencode from blocking on stdin
            stdout=stdout_f,
            stderr=stderr_f,
            text=True,
            encoding="utf-8",
            timeout=effective_timeout,
            check=False,
            env=build_subprocess_env(model),
        )

        stdout_f.seek(0)
        stdout_data = stdout_f.read()
        stderr_f.seek(0)
        stderr_data = stderr_f.read()

    return proc.returncode, stdout_data, stderr_data


def _execute_task(
    task_path: Path,
    outbox_dir: Path,
    model: str | None,
    effort: str | None,
    attempt: int,
) -> bool:
    """Execute a single task attempt."""
    task_id = task_path.stem.split(".")[0]

    task_data = load_and_validate_task(task_path)
    if task_data is None:
        write_error_envelope(task_id, "Task validation failed: invalid or oversized task file", outbox_dir)
        return False

    actual_task_id = task_data.get("task_id", task_id)
    combined_prompt = build_combined_prompt(task_data)

    effective_model = model or os.environ.get("OPENCODE_MODEL") or os.environ.get("MYKG_MODEL") or DEFAULT_MODEL
    effective_effort = effort or os.environ.get("OPENCODE_EFFORT") or os.environ.get("MYKG_EFFORT") or "minimal"

    print(
        f"[opencode_daemon] Running opencode for task {task_id[:12]} (prompt size: {len(combined_prompt)} chars)...",
        flush=True,
    )

    # SECURITY: Compute effective timeout with hard cap to prevent DoS.
    # The task's timeout_seconds is the orchestrator's patience ceiling.
    # The dynamic formula provides a floor based on prompt size.
    effective_timeout = compute_effective_timeout(
        task_data.get("timeout_seconds"),
        len(combined_prompt),
    )

    # Cap the wall-clock wait for a single CLI invocation.
    #
    # compute_effective_timeout() returns a floor of 600s and honours the task's
    # timeout_seconds (1800s in practice), so an invocation that never returns
    # parks a worker for up to half an hour. The CLI hangs intermittently -- the
    # server finishes its database bootstrap and then goes idle with the client
    # still waiting, having made no network attempt -- and with a single worker
    # that stalls the entire queue.
    #
    # A 118KB prompt completes in ~13s, so a few minutes is generous headroom for
    # a slow model. Anything longer than that is treated as a hang: the attempt
    # fails, the retry budget applies, and other workers keep working.
    effective_timeout = min(effective_timeout, MAX_CLI_TIMEOUT)

    print(f"[opencode_daemon] Using timeout: {effective_timeout}s for task {task_id[:12]}", flush=True)

    # opencode v2 removed `--pure` and `--variant` from `opencode run`; passing
    # either makes the CLI print its usage block and exit 1 without ever
    # contacting the model. The variant is a `#suffix` on the model string.
    #
    # Variant availability is per-model, and a bad pick is fatal in v2, so walk
    # the effort ladder and degrade on rejection rather than failing the task.
    candidates = variant_candidates(effective_effort)
    returncode = 1
    stdout_data = ""
    stderr_data = ""

    for index, variant in enumerate(candidates):
        # `--standalone` runs a private server in-process instead of spawning
        # `opencode serve --service` and waiting for it to become ready. That
        # background server intermittently spins at 100% CPU without ever
        # becoming ready, which left `opencode run` blocked until the task
        # timeout -- and with a single worker that stalled the whole queue.
        # Standalone mode has no such process, so the failure mode is gone
        # rather than merely bounded.
        cmd = ["opencode", "run", "--standalone", "--auto", "-m", build_model_spec(effective_model, variant)]
        cmd.append(combined_prompt)

        returncode, stdout_data, stderr_data = _run_opencode(cmd, effective_timeout, effective_model)

        if returncode == 0:
            break

        is_last = index == len(candidates) - 1
        if is_last or not is_variant_unavailable(stderr_data):
            break

        next_variant = candidates[index + 1]
        print(
            f"[opencode_daemon] Variant '{variant}' unavailable for {effective_model}; retrying with {next_variant or 'no variant'}.",
            file=sys.stderr,
            flush=True,
        )

    print(f"[opencode_daemon] opencode returned code {returncode} for task {task_id[:12]}", flush=True)

    if returncode != 0:
        # Surface stderr: a bare exit code hides the actual cause, which is
        # exactly how a v2 CLI flag/model regression went unnoticed here.
        detail = (stderr_data or "").strip().splitlines()
        reason = detail[-1][:300] if detail else "no stderr output"
        write_error_envelope(task_id, f"Subprocess failed with exit code {returncode}: {reason}", outbox_dir)
        print(
            f"[opencode_daemon] Warning: opencode failed for {task_id}: exit code {returncode} — {reason}",
            file=sys.stderr,
            flush=True,
        )
        return False

    answer_text = clean_json_fences(stdout_data)
    write_answer_envelope(task_id, answer_text, outbox_dir, actual_task_id)
    print(f"[opencode_daemon] Processed task {task_id[:12]}", flush=True)
    return True


def run_daemon(
    inbox_dir: Path,
    outbox_dir: Path,
    workers: int = 2,
    poll_interval: float = 2.0,
    model: str | None = None,
    effort: str | None = None,
) -> None:
    """Watch inbox_dir and dispatch task processing in a thread pool."""
    # Bootstrap opencode auth from secret mount
    bootstrap_opencode_auth()
    # Pin the auxiliary model so opencode does not pick a paid default of its own.
    write_opencode_small_model_config(model)

    effective_model = model or os.environ.get("OPENCODE_MODEL") or os.environ.get("MYKG_MODEL") or DEFAULT_MODEL
    effective_effort = effort or os.environ.get("OPENCODE_EFFORT") or os.environ.get("MYKG_EFFORT") or "minimal"

    _run_daemon_core(
        inbox_dir=inbox_dir,
        outbox_dir=outbox_dir,
        process_fn=process_task,
        workers=workers,
        poll_interval=poll_interval,
        model=effective_model,
        effort=effective_effort,
        daemon_name="opencode_daemon",
    )


def main() -> None:
    """Parse CLI arguments and run daemon."""
    parser = argparse.ArgumentParser(description="Daemon for processing myKG tasks via opencode CLI.")
    parser.add_argument("inbox_dir", type=Path, help="Path to agent_inbox directory or session root")
    parser.add_argument("outbox_dir", type=Path, help="Path to agent_outbox directory or session root")
    parser.add_argument("--workers", type=int, default=2, help="Number of concurrent worker threads")
    parser.add_argument("--poll-interval", type=float, default=2.0, help="Polling interval in seconds")
    parser.add_argument(
        "--model",
        "-m",
        default=os.environ.get("OPENCODE_MODEL") or os.environ.get("MYKG_MODEL") or DEFAULT_MODEL,
        help=f"Model to use for opencode CLI (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--effort",
        "-e",
        choices=["low", "medium", "high", "minimal"],
        default=os.environ.get("OPENCODE_EFFORT") or os.environ.get("MYKG_EFFORT") or "minimal",
        help="Reasoning effort for opencode CLI (default: minimal)",
    )

    args = parser.parse_args()
    run_daemon(
        inbox_dir=args.inbox_dir,
        outbox_dir=args.outbox_dir,
        workers=args.workers,
        poll_interval=args.poll_interval,
        model=args.model,
        effort=args.effort,
    )


if __name__ == "__main__":
    main()

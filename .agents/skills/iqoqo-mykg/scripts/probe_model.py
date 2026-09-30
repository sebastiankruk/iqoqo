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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
"""Run one opencode model call inside the sandbox, with hang diagnostics.

WHY THIS EXISTS
    `opencode run --standalone` intermittently never returns. The captured
    signature is: it spawns `opencode serve --stdio`, that server finishes its
    "database schema bootstrap", and then both processes sleep in ep_poll with
    no network attempt at all -- a deadlock, not a busy loop. It reproduces
    roughly once in fifty runs, so inspecting the container after the fact is
    usually impossible: `compose run --rm` has already removed it.

    This script runs *inside* the container, so on timeout it can still read
    its own /proc and the opencode log before the container disappears. That
    turns an unreproducible hang into recorded evidence.

Exit status:
    0  model answered
    1  the CLI failed (its stderr is reported)
    2  the CLI hung; diagnostics were printed
"""

import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, "/workspace/.agents/skills/iqoqo-mykg/scripts")

from opencode_daemon import (  # noqa: E402
    bootstrap_opencode_auth,
    build_subprocess_env,
    write_opencode_small_model_config,
)

OPENCODE_LOG = Path.home() / ".local" / "share" / "opencode" / "log" / "opencode.log"


def dump_diagnostics(elapsed: float) -> None:
    """Record enough state to diagnose a hang, while the container still exists."""
    print(f"\n===== HANG DIAGNOSTICS (waited {elapsed:.0f}s) =====", file=sys.stderr)

    print("--- processes (pid state cmd) ---", file=sys.stderr)
    for entry in sorted(Path("/proc").glob("[0-9]*")):
        pid = entry.name
        try:
            cmd = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace").strip()
            if not cmd:
                continue
            comm = (entry / "comm").read_text().strip()
            stat = (entry / "stat").read_text().split()
            state = stat[2] if len(stat) > 2 else "?"
            try:
                wchan = (entry / "wchan").read_text().strip()
            except OSError:
                wchan = "?"
            print(f"  pid={pid} comm={comm} state={state} wchan={wchan} :: {cmd[:160]}", file=sys.stderr)
        except OSError:
            continue

    print("--- opencode log ---", file=sys.stderr)
    try:
        for line in OPENCODE_LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-30:]:
            print(f"  {line[:200]}", file=sys.stderr)
    except OSError as err:
        print(f"  (unavailable: {err})", file=sys.stderr)

    print("--- proxy env inherited by the opencode child ---", file=sys.stderr)
    # Report what the CHILD will see, not this process. The key is injected
    # per-child via build_subprocess_env(), so it is legitimately absent here --
    # reporting this process's env produced a misleading "<unset>".
    child_env = build_subprocess_env(sys.argv[1] if len(sys.argv) > 1 else None)
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "NO_PROXY", "OPENCODE_API_KEY"):
        value = child_env.get(key)
        if value is None:
            print(f"  {key}=<unset>", file=sys.stderr)
        elif "KEY" in key:
            print(f"  {key}=<set, {len(value)} chars>", file=sys.stderr)
        elif "PROXY" in key:
            print(f"  {key}={value}", file=sys.stderr)
        else:
            print(f"  {key}=<set, {len(value)} chars>", file=sys.stderr)
    print("===== END DIAGNOSTICS =====", file=sys.stderr)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: probe_model.py <provider/model#variant> [prompt] [timeout]", file=sys.stderr)
        return 2

    model = sys.argv[1]
    prompt = sys.argv[2] if len(sys.argv) > 2 else "reply with the single word OK"
    timeout = int(sys.argv[3]) if len(sys.argv) > 3 else 120

    bootstrap_opencode_auth()
    write_opencode_small_model_config(model)

    cmd = ["opencode", "run", "--standalone", "--auto", "-m", model, prompt]
    print(f"[probe_model] {model} (timeout {timeout}s)", file=sys.stderr, flush=True)

    started = time.time()
    try:
        # Temp files, NOT capture_output=True. This is the same deadlock the
        # daemon's "_run_opencode" already guards against: `opencode run`
        # spawns `serve --stdio`, and if the client exits while the server
        # lingers, the server keeps the inherited stdout/stderr pipe write end
        # open. subprocess.run() then blocks forever waiting for EOF on a pipe
        # whose writer is an orphaned 100%-CPU process -- the child has already
        # exited, so it looks like a hang with nothing running to explain it.
        with (
            tempfile.TemporaryFile(mode="w+", encoding="utf-8", suffix=".stdout") as out_f,
            tempfile.TemporaryFile(mode="w+", encoding="utf-8", suffix=".stderr") as err_f,
        ):
            proc = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=out_f,
                stderr=err_f,
                text=True,
                encoding="utf-8",
                timeout=timeout,
                env=build_subprocess_env(model),
            )
            out_f.seek(0)
            stdout_data = out_f.read()
            err_f.seek(0)
            stderr_data = err_f.read()
        result = subprocess.CompletedProcess(cmd, proc.returncode, stdout_data, stderr_data)
    except subprocess.TimeoutExpired:
        dump_diagnostics(time.time() - started)
        return 2

    elapsed = time.time() - started
    if result.returncode != 0:
        print(f"[probe_model] rc={result.returncode} after {elapsed:.1f}s", file=sys.stderr)
        print(result.stderr[-800:], file=sys.stderr)
        return 1

    print(result.stdout[-400:])
    print(f"[probe_model] ok in {elapsed:.1f}s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

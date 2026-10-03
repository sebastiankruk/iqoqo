#!/usr/bin/env python3
"""
Fail the container build when an image exceeds its declared size budget.

The target used to be a number in a prose requirement ("under 500 MB"), which
went unmet through an entire release without anything failing -- prose cannot
fail. This makes it executable: read the built image's real size, compare it
against deploy/image-size-budget.txt, and exit non-zero over the limit. On
failure it prints the per-path breakdown of what is taking the space, so the
cause is identifiable without rebuilding to investigate.

Run via: python scripts/check_image_size.py <image>
Called automatically by scripts/build_docker_images.sh after the backend build.
"""

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

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BUDGET_FILE = ROOT / "deploy" / "image-size-budget.txt"
DEFAULT_IMAGE = "iqoqo-backend:latest"

MB = 1024 * 1024

# Paths worth attributing by name when the budget is blown. A bare `du /`
# answers "the image is big"; these answer "scipy came back".
WATCHED_PATHS = (
    "/usr/local/lib/python3.14/site-packages",
    "/usr/local/lib/python3.14",
    "/usr/lib/x86_64-linux-gnu",
    "/usr/share",
    "/usr/src/app",
    "/usr/local/bin",
)

# Individual site-packages directories, so a single fat dependency is named
# rather than hidden inside the 400 MB site-packages total.
_SITE_PACKAGES = "/usr/local/lib/python3.14/site-packages"

REQUIRED_KEYS = ("MAX_BYTES", "MEASURED_BYTES")
"""Keys the budget file must define. Both, because MAX_BYTES without a recorded
MEASURED_BYTES is the old prose-requirement failure mode: a number nobody can
explain, and therefore nobody dares to lower."""


def parse_budget(text: str) -> dict[str, int]:
    """Parse the budget file's ``KEY=value`` pairs.

    Returns:
        A mapping of the recognised keys to integers.

    Raises:
        ValueError: If a recognised key is malformed, not a positive integer, or
            absent. A budget that cannot be parsed must fail loudly rather than
            defaulting to "unlimited", which would silently disable the gate.
    """
    found: dict[str, int] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key not in REQUIRED_KEYS:
            continue
        try:
            number = int(value.strip())
        except ValueError as exc:
            raise ValueError(f"{key} is not an integer: {value.strip()!r}") from exc
        if number <= 0:
            raise ValueError(f"{key} must be positive, got {number}")
        found[key] = number

    missing = [key for key in REQUIRED_KEYS if key not in found]
    if missing:
        raise ValueError(f"{', '.join(missing)} not found in budget file")
    if found["MEASURED_BYTES"] > found["MAX_BYTES"]:
        raise ValueError(f"MEASURED_BYTES ({found['MEASURED_BYTES']}) exceeds MAX_BYTES ({found['MAX_BYTES']})")
    return found


def read_budget(path: Path = DEFAULT_BUDGET_FILE) -> dict[str, int]:
    """Load and parse the budget file."""
    return parse_budget(path.read_text(encoding="utf-8"))


def format_mb(byte_count: int) -> str:
    """Render bytes as MiB with one decimal, for humans."""
    return f"{byte_count / MB:.1f} MB"


def evaluate(actual_bytes: int, budget_bytes: int) -> tuple[bool, str]:
    """Compare a measured size against the budget.

    Returns:
        ``(within_budget, message)``. Pure, so the gate's behaviour can be
        asserted in tests without a Docker daemon or a real image.
    """
    if actual_bytes <= budget_bytes:
        headroom = budget_bytes - actual_bytes
        return True, f"{format_mb(actual_bytes)} within budget of {format_mb(budget_bytes)} ({format_mb(headroom)} to spare)"
    over = actual_bytes - budget_bytes
    return False, f"{format_mb(actual_bytes)} EXCEEDS budget of {format_mb(budget_bytes)} by {format_mb(over)}"


def image_size(image: str) -> int:
    """Return the uncompressed size of ``image`` in bytes.

    Uses the same call the gate is specified against, so the number compared is
    the measured one rather than an estimate from layer metadata.
    """
    result = subprocess.run(
        ["docker", "image", "inspect", image, "--format", "{{.Size}}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        sys.exit(f"error: cannot inspect image {image!r}: {detail}")
    try:
        return int(result.stdout.strip())
    except ValueError:
        sys.exit(f"error: unexpected `docker image inspect` output: {result.stdout.strip()!r}")


def _du(image: str, path: str) -> int | None:
    """Return the on-disk size of ``path`` inside ``image``, in MiB."""
    result = subprocess.run(
        ["docker", "run", "--rm", "--entrypoint", "du", image, "-sm", "--", path],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    first = result.stdout.split("\t")[0].strip()
    return int(first) if first.isdigit() else None


def _du_children(image: str, parent: str) -> list[tuple[int, str]]:
    """Return ``(size_mb, path)`` for each direct child of ``parent`` in ``image``.

    Runs through ``sh`` because ``du`` does not expand the glob itself and
    ``docker run`` has no shell unless one is asked for. Only ``parent`` reaches
    the shell command string -- it is a constant -- while the image reference
    stays an argv element, so nothing user-supplied is ever interpolated into
    shell syntax.
    """
    result = subprocess.run(
        ["docker", "run", "--rm", "--entrypoint", "sh", image, "-c", f"du -sm -- {parent}/*"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []

    children: list[tuple[int, str]] = []
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 2 and parts[0].strip().isdigit():
            children.append((int(parts[0].strip()), parts[1].strip()))
    return children


def breakdown(image: str, limit: int = 15) -> str:
    """Print, and return, a per-path size breakdown of ``image``.

    Run against the image that is already built, which is the point: the gate's
    job is to make the cause findable without a second multi-minute build.
    """
    if shutil.which("du") is None:
        return "  (du not available in the runtime stage; install coreutils to get a breakdown)"

    lines = ["", f"Size breakdown of {image} (the biggest consumers first):", ""]

    entries: list[tuple[int, str]] = []
    for path in WATCHED_PATHS:
        size = _du(image, path)
        if size is not None:
            entries.append((size, path))
    entries.sort(reverse=True)

    for size_mb, path in entries:
        lines.append(f"  {size_mb:>7} MB  {path}")

    # Name individual packages inside site-packages: a dependency quietly pulling
    # in 30 MB of numeric libraries is the failure this gate exists to catch.
    packages = _du_children(image, _SITE_PACKAGES)
    if packages:
        packages.sort(reverse=True)
        lines.append("")
        lines.append(f"  Largest packages under {_SITE_PACKAGES}:")
        for size_mb, path in packages[:limit]:
            lines.append(f"  {size_mb:>7} MB  {path.removeprefix(_SITE_PACKAGES + '/')}")

    lines.append("")
    lines.append(f"  Budget and its recorded measurement are in {DEFAULT_BUDGET_FILE.relative_to(ROOT)}.")
    lines.append("  Raising MAX_BYTES is allowed; raising it without updating MEASURED_BYTES")
    lines.append("  in the same commit defeats the purpose of having one.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("image", nargs="?", default=DEFAULT_IMAGE, help="image reference to check")
    parser.add_argument("--budget-file", type=Path, default=DEFAULT_BUDGET_FILE, help="budget file to enforce")
    parser.add_argument("--quiet", action="store_true", help="print nothing when within budget")
    args = parser.parse_args()

    try:
        budget = read_budget(args.budget_file)
    except (OSError, ValueError) as exc:
        sys.exit(f"error: cannot read size budget from {args.budget_file}: {exc}")

    actual = image_size(args.image)
    within_budget, message = evaluate(actual, budget["MAX_BYTES"])

    if within_budget:
        if not args.quiet:
            print(f"✅ image size gate: {args.image} — {message}")
            print(f"   recorded measurement: {format_mb(budget['MEASURED_BYTES'])}")
        return 0

    print(f"❌ image size gate FAILED for {args.image}: {message}", file=sys.stderr)
    print(
        f"   last recorded measurement: {format_mb(budget['MEASURED_BYTES'])} "
        f"(growth since then: {format_mb(actual - budget['MEASURED_BYTES'])})",
        file=sys.stderr,
    )
    print(breakdown(args.image), file=sys.stderr)
    print(
        f"Either remove the growth, or raise MAX_BYTES and MEASURED_BYTES in {args.budget_file} together.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())

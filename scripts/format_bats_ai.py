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
"""Terse TAP formatter for BATS test suites under IQOQO_AI_MODE."""

from __future__ import annotations

import sys


def main() -> int:
    """Format TAP stream from stdin into terse dot progress and failure report."""
    passed = 0
    failed: list[list[str]] = []
    cur_fail: list[str] | None = None
    all_lines: list[str] = []

    for line in sys.stdin:
        all_lines.append(line)
        if line.startswith("ok "):
            if cur_fail:
                failed.append(cur_fail)
                cur_fail = None
            passed += 1
            sys.stdout.write(".")
            sys.stdout.flush()
        elif line.startswith("not ok "):
            if cur_fail:
                failed.append(cur_fail)
            cur_fail = [line]
            sys.stdout.write("F")
            sys.stdout.flush()
        elif cur_fail is not None:
            cur_fail.append(line)

    if cur_fail:
        failed.append(cur_fail)

    if passed > 0 or failed:
        sys.stdout.write("\n")
        if failed:
            sys.stdout.write("\n" + "=" * 60 + "\nBATS FAILURES:\n" + "=" * 60 + "\n")
            for chunk in failed:
                sys.stdout.write("".join(chunk))
            sys.stdout.write(f"\nFAILED ({len(failed)} failed, {passed} passed)\n")
            return 1

        sys.stdout.write(f"BATS: {passed} tests passed.\n")
        return 0

    # If neither passed nor failed matched (e.g. syntax or runtime error in bats)
    sys.stdout.write("".join(all_lines))
    return 1


if __name__ == "__main__":
    sys.exit(main())

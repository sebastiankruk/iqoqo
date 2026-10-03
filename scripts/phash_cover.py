#!/usr/bin/env python3
"""
Print the perceptual hash of one or more cover images.

The value is what IQOQO_KNOWN_JUNK_PHASHES holds, so this is how an operator
(a) hashes a placeholder they want blocked and (b) checks that hashes stored
before the ImageHash removal still resolve under the current algorithm.

Usage:
    python scripts/phash_cover.py junk_cover.jpg another.png
    python scripts/phash_cover.py --check junk_cover.jpg

With --check, each image is hashed and looked up in IQOQO_KNOWN_JUNK_PHASHES, and
the exit status is non-zero if any of them is NOT in the list. That is the
verification step for the ImageHash removal: run it against a placeholder you
know is blocked and confirm it still reports "blocked".

Run via: docker compose exec web python scripts/phash_cover.py <image> [...]
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
import os
import sys

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

from PIL import Image, UnidentifiedImageError

from app.utils.images import KNOWN_JUNK_PHASHES
from app.utils.phash import parse_hash, perceptual_hash


def hash_file(path: str) -> str:
    """Hash the image at ``path``, or exit with a message naming the file."""
    try:
        with Image.open(path) as image:
            return perceptual_hash(image)
    except FileNotFoundError:
        sys.exit(f"error: no such file: {path}")
    except UnidentifiedImageError:
        sys.exit(f"error: not an image file: {path}")
    except OSError as exc:
        sys.exit(f"error: cannot read {path}: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("images", nargs="+", metavar="IMAGE", help="image file(s) to hash")
    parser.add_argument(
        "--check",
        action="store_true",
        help="report whether each image is blocked by IQOQO_KNOWN_JUNK_PHASHES; exit 1 if any is not",
    )
    args = parser.parse_args()

    unknown_misses = 0

    for path in args.images:
        computed = hash_file(path)

        if not args.check:
            print(f"{computed}  {path}")
            continue

        # Anything already loaded and well-formed is what is_valid_cover will
        # compare against, so report against that set rather than re-parsing.
        if computed in KNOWN_JUNK_PHASHES:
            print(f"blocked   {computed}  {path}")
        else:
            print(f"ACCEPTED  {computed}  {path}")
            unknown_misses += 1

    if args.check:
        print(f"\n{len(KNOWN_JUNK_PHASHES)} known-junk pHash(es) configured.", file=sys.stderr)
        print(f"{unknown_misses} of {len(args.images)} image(s) not blocked.", file=sys.stderr)
        # Validate what is configured too: an entry that no longer parses is
        # silently ignored by the app, which is the failure mode this catches.
        for entry in os.getenv("IQOQO_KNOWN_JUNK_PHASHES", "").split(","):
            if entry.strip():
                try:
                    parse_hash(entry)
                except ValueError as exc:
                    print(f"warning: ignoring unusable configured pHash {entry.strip()!r}: {exc}", file=sys.stderr)
                    unknown_misses += 1

    return 1 if unknown_misses else 0


if __name__ == "__main__":
    sys.exit(main())

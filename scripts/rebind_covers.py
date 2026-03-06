#!/usr/bin/env python3
"""
Script to re-bind orphaned cover images to books that are missing covers.
Run this before archiving orphans to ensure valid covers are not deleted.
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
#

import os
import sys

# Add the project root to the Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

from app import create_app
from app.utils.covers import rebind_orphaned_covers


def main():
    app = create_app()
    with app.app_context():
        print("Starting cover rebind process...")
        count = rebind_orphaned_covers()
        print(f"Rebound {count} covers.")


if __name__ == "__main__":
    main()

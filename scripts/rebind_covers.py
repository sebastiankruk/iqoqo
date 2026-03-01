#!/usr/bin/env python3
"""
Script to re-bind orphaned cover images to books that are missing covers.
Run this before archiving orphans to ensure valid covers are not deleted.
"""
import os
import sys

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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

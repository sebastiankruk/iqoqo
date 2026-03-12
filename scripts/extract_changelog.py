import re
import sys


def extract_release_notes(version: str) -> None:
    try:
        with open("docs/CHANGELOG.md", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print("No CHANGELOG.md found.")
        sys.exit(0)

    # Look for the section starting with ## [version] and ending at the next ## [
    pattern = rf"## \[{re.escape(version)}\].*?\n(.*?)(?=\n## \[|$)"
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)

    if match:
        print(match.group(1).strip())
    else:
        print(f"No release notes found for version {version}.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/extract_changelog.py <version>")
        sys.exit(1)

    extract_release_notes(sys.argv[1])

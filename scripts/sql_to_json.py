"""
Convert legacy SQL dump to JSON format for migration.

This script parses the legacy iqoqo SQL dump and converts it to a JSON format
that can be used by the migrate_legacy.py script.

Usage:
    python scripts/sql_to_json.py <input.sql> <output.json>
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def _parse_sql_values(values_str: str) -> list[str | None]:
    """
    Parse a comma-separated PostgreSQL VALUES string into a list of Python values.

    Handles SQL single-quoted strings (with ``''`` as escaped single quote) and
    unquoted NULL literals.

    Args:
        values_str: The raw content between the outer parentheses of VALUES (...).

    Returns:
        List of string values (or None for SQL NULL).
    """
    result: list[str | None] = []
    current: list[str] = []
    in_quote = False
    i = 0

    while i < len(values_str):
        ch = values_str[i]
        if in_quote:
            if ch == "'" and i + 1 < len(values_str) and values_str[i + 1] == "'":
                # SQL-escaped single quote: '' → '
                current.append("'")
                i += 2
                continue

            if ch == "'":
                # End of quoted string
                in_quote = False
            else:
                current.append(ch)
        else:
            if ch == "'":
                in_quote = True
            elif ch == ",":
                token = "".join(current).strip()
                result.append(None if token == "NULL" else token)
                current = []
                i += 1
                continue
            else:
                current.append(ch)
        i += 1

    # Append the last value
    token = "".join(current).strip()
    result.append(None if token == "NULL" else token)

    return result


def _split_row_tuples(values_block: str) -> list[str]:
    """
    Extract the inner content of each top-level ``(…)`` tuple in a VALUES block.

    Correctly handles SQL single-quoted strings (which may contain commas and
    parentheses) so that only structural parentheses are used as boundaries.

    Args:
        values_block: Everything after ``VALUES`` up to but not including the
                      trailing ``;``.

    Returns:
        List of strings, each being the raw content between the outer parens
        of one row, suitable for passing to :func:`_parse_sql_values`.
    """
    rows: list[str] = []
    depth = 0
    start = -1
    in_quote = False
    i = 0
    n = len(values_block)

    while i < n:
        ch = values_block[i]
        if in_quote:
            if ch == "'" and i + 1 < n and values_block[i + 1] == "'":
                # Escaped single-quote: skip both characters
                i += 2
                continue
            if ch == "'":
                in_quote = False
        else:
            if ch == "'":
                in_quote = True
            elif ch == "(" and depth == 0:
                depth = 1
                start = i + 1
            elif ch == "(":
                depth += 1
            elif ch == ")" and depth == 1:
                rows.append(values_block[start:i])
                depth = 0
                start = -1
            elif ch == ")":
                depth -= 1
        i += 1

    return rows


def parse_sql_dump(sql_content: str) -> dict:
    """
    Parse a legacy SQL dump and extract data.

    Supports both quoted (``"iqoqo"."table"``) and unquoted (``iqoqo.table``)
    schema-qualified table names as produced by different pg_dump versions.

    Args:
        sql_content: Content of the SQL dump file.

    Returns:
        Dictionary containing clients, manifestations, and items.
    """
    data: dict[str, list] = {
        "clients": [],
        "manifestations": [],
        "items": [],
    }

    # ── Step 1: join multi-line INSERT statements into single logical lines ──
    # pg_dump may emit the VALUES keyword and individual rows on separate lines.
    # We collect lines that belong to the same statement (from INSERT to the
    # line ending with ";") and join them so the regex can work on one string.
    statements: list[str] = []
    buffer: list[str] = []
    for raw_line in sql_content.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        if stripped.upper().startswith("INSERT INTO"):
            buffer = [stripped]
        elif buffer:
            buffer.append(stripped)
        if buffer and stripped.endswith(";"):
            statements.append(" ".join(buffer))
            buffer = []

    # ── Step 2: parse each statement ────────────────────────────────────────
    # Handles both:
    #   INSERT INTO "iqoqo"."table" (col, …) VALUES (…), (…);
    #   INSERT INTO iqoqo.table VALUES (…);
    insert_re = re.compile(
        r"INSERT\s+INTO\s+"
        r'(?:"?iqoqo"?\.)"?(\w+)"?'  # schema + table name (group 1)
        r"(?:\s*\([^)]*\))?\s*VALUES\s+"  # optional column list + VALUES keyword
        r"(.+?)\s*;?\s*$",  # values block (group 2)
        re.IGNORECASE,
    )

    for stmt in statements:
        m = insert_re.match(stmt)
        if not m:
            continue

        table_name = m.group(1)
        values_block = m.group(2)

        for row_content in _split_row_tuples(values_block):
            values = _parse_sql_values(row_content)

            if table_name == "client" and len(values) >= 4:
                data["clients"].append(
                    {
                        "id": values[0],
                        "address": values[1],
                        "user": values[2],
                        "added": values[3],
                    }
                )
            elif table_name == "manifestation" and len(values) >= 5:
                # Columns: id, isbn, title, authors, meta (JSON), added
                meta: dict[str, Any] = {}
                try:
                    meta = json.loads(values[4]) if values[4] else {}
                except (json.JSONDecodeError, TypeError):
                    pass

                data["manifestations"].append(
                    {
                        "id": values[0],
                        "isbn": values[1],
                        "title": values[2],
                        "authors": values[3],
                        "meta": meta,
                        "added": values[5] if len(values) > 5 else None,
                    }
                )
            elif table_name == "item" and len(values) >= 4:
                # Columns: id, manifestation_id, added_by, added_at, meta (JSON)
                item_meta: dict[str, Any] = {}
                try:
                    item_meta = json.loads(values[4]) if len(values) > 4 and values[4] else {}
                except (json.JSONDecodeError, TypeError):
                    pass

                data["items"].append(
                    {
                        "id": values[0],
                        "manifestation_id": values[1],
                        "added_by": values[2],
                        "added_at": values[3],
                        "meta": item_meta,
                    }
                )

    return data


def main():
    """Main entry point for SQL to JSON conversion."""
    parser = argparse.ArgumentParser(description="Convert legacy SQL dump to JSON format")
    parser.add_argument("input_file", help="Path to SQL dump file")
    parser.add_argument("output_file", help="Path to output JSON file")
    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    print(f"Reading SQL dump from {input_path}...")
    with open(input_path, encoding="utf-8") as f:
        sql_content = f.read()

    print("Parsing SQL dump...")
    data = parse_sql_dump(sql_content)

    print(f"Found {len(data['clients'])} clients")
    print(f"Found {len(data['manifestations'])} manifestations")
    print(f"Found {len(data['items'])} items")

    output_path = Path(args.output_file)
    print(f"Writing JSON to {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("Conversion complete!")


if __name__ == "__main__":
    main()

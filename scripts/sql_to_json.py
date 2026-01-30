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


def parse_sql_dump(sql_content: str) -> dict:
    """
    Parse a legacy SQL dump and extract data.

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

    # Extract INSERT statements - handle multiple INSERT statements
    # Pattern to match INSERT INTO...VALUES and capture everything until the next INSERT or end
    insert_pattern = r"INSERT INTO \"iqoqo\"\.\"(\w+)\" \([^)]+\) VALUES\s*(.*?)(?=INSERT INTO|ALTER TABLE|\Z)"

    matches = re.finditer(insert_pattern, sql_content, re.DOTALL)

    for match in matches:
        table_name = match.group(1)
        values_str = match.group(2)

        # Parse individual value tuples
        # Need to handle nested structures and quotes properly
        # Find tuples by balancing parentheses while tracking quote state
        tuples = []
        depth = 0
        current_tuple = []
        i = 0
        in_quote = False
        while i < len(values_str):
            char = values_str[i]

            # Handle single quotes (string delimiters in SQL)
            if char == "'" and (i == 0 or values_str[i - 1] != "\\"):
                in_quote = not in_quote
                if depth > 0:
                    current_tuple.append(char)
            elif char == "(" and not in_quote and depth == 0:
                depth = 1
                current_tuple = []
            elif char == "(" and not in_quote:
                depth += 1
                current_tuple.append(char)
            elif char == ")" and not in_quote and depth == 1:
                depth = 0
                tuples.append("".join(current_tuple))
                current_tuple = []
            elif char == ")" and not in_quote:
                depth -= 1
                current_tuple.append(char)
            elif depth > 0:
                current_tuple.append(char)
            i += 1

        for tuple_str in tuples:
            # Split by comma, but respect quotes
            values = []
            current = []
            in_quotes = False
            escape_next = False

            for char in tuple_str + ",":
                if escape_next:
                    current.append(char)
                    escape_next = False
                    continue

                if char == "\\":
                    escape_next = True
                    continue

                if char == "'" and not in_quotes:
                    in_quotes = True
                    continue

                if char == "'" and in_quotes:
                    in_quotes = False
                    continue

                if char == "," and not in_quotes:
                    values.append("".join(current).strip())
                    current = []
                    continue

                current.append(char)

            # Clean up values
            cleaned_values = []
            for v in values:
                v = v.strip()
                if v.startswith("'") and v.endswith("'"):
                    v = v[1:-1]
                cleaned_values.append(v)

            # Map to appropriate table
            if table_name == "client" and len(cleaned_values) >= 4:
                data["clients"].append(
                    {
                        "id": cleaned_values[0],
                        "address": cleaned_values[1],
                        "user": cleaned_values[2],
                        "added": cleaned_values[3],
                    }
                )
            elif table_name == "manifestation" and len(cleaned_values) >= 6:
                # Manifestation table has: id, isbn, title, authors, meta (JSON), added
                # Parse meta JSON if present
                meta: dict[str, Any] = {}
                if len(cleaned_values) > 4:
                    try:
                        meta = json.loads(cleaned_values[4]) if cleaned_values[4] else {}
                    except json.JSONDecodeError:
                        pass

                data["manifestations"].append(
                    {
                        "id": cleaned_values[0],
                        "isbn": cleaned_values[1] if len(cleaned_values) > 1 else None,
                        "title": cleaned_values[2] if len(cleaned_values) > 2 else None,
                        "authors": cleaned_values[3] if len(cleaned_values) > 3 else None,
                        "meta": meta,
                        "added": cleaned_values[5] if len(cleaned_values) > 5 else None,
                    }
                )
            elif table_name == "item" and len(cleaned_values) >= 5:
                # Parse meta JSON if present
                meta = {}
                if len(cleaned_values) > 4:
                    try:
                        meta = json.loads(cleaned_values[4]) if cleaned_values[4] else {}
                    except json.JSONDecodeError:
                        pass

                data["items"].append(
                    {
                        "id": cleaned_values[0],
                        "manifestation_id": cleaned_values[1],
                        "added_by": cleaned_values[2],
                        "added_at": cleaned_values[3],
                        "meta": meta,
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

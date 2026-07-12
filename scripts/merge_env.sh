#!/bin/bash
# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

STAGE=""
TARGET_FILE=""
ENV_FILE=".env"

usage() {
    echo "Usage: $0 <preview|prod> [--dry-run] [--root DIR]"
    echo ""
    echo "  Merges $ENV_FILE into .env.<stage> (target values win on conflicts),"
    echo "  backs up $ENV_FILE -> ${ENV_FILE}.bak, and symlinks $ENV_FILE -> .env.<stage>."
    echo ""
    echo "  <stage>      Target stage name (preview or prod)"
    echo "  --dry-run    Show what would be added without modifying files"
    echo "  --root DIR   Use DIR as project root (default: auto-detect from script location)"
    exit 1
}

DRY_RUN=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        preview|prod)
            STAGE="$1"
            TARGET_FILE=".env.${STAGE}"
            shift
            ;;
        --dry-run) DRY_RUN=true; shift ;;
        --root) PROJECT_ROOT="$2"; shift 2 ;;
        -h|--help) usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

if [[ -z "$STAGE" ]]; then
    echo "Error: stage name required (preview or prod)" >&2
    usage
fi

cd "$PROJECT_ROOT"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "Error: $ENV_FILE not found" >&2
    exit 1
fi
if [[ ! -f "$TARGET_FILE" ]]; then
    echo "Error: $TARGET_FILE not found" >&2
    exit 1
fi

# Load values from both files
declare -A target_keys
declare -A env_keys

extract_keyval() {
    local line="$1"
    echo "$line" | grep -oP '^\s*\K[A-Za-z_][A-Za-z0-9_]*\s*=\s*.*' 2>/dev/null || true
}

while IFS='=' read -r key val; do
    key="${key## }"; key="${key%% }"
    [[ -z "$key" || "$key" == \#* ]] && continue
    env_keys["$key"]="$val"
done < "$ENV_FILE"

while IFS='=' read -r key val; do
    key="${key## }"; key="${key%% }"
    [[ -z "$key" || "$key" == \#* ]] && continue
    target_keys["$key"]="$val"
done < "$TARGET_FILE"

# Find keys in .env but not in target
new_keys=()
for key in "${!env_keys[@]}"; do
    if [[ -z "${target_keys[$key]:-}" ]]; then
        new_keys+=("$key")
    fi
done

if [[ ${#new_keys[@]} -eq 0 ]]; then
    echo "No missing keys to merge. $TARGET_FILE already covers everything from $ENV_FILE."
    if [[ ! -L "$ENV_FILE" ]]; then
        echo "Creating symlink: $ENV_FILE -> $TARGET_FILE"
        if [[ "$DRY_RUN" != "true" ]]; then
            cp "$ENV_FILE" "${ENV_FILE}.bak"
            rm "$ENV_FILE"
            ln -s "$TARGET_FILE" "$ENV_FILE"
        fi
    else
        echo "$ENV_FILE is already a symlink."
    fi
    exit 0
fi

echo "Adding ${#new_keys[@]} missing key(s) to $TARGET_FILE:"
for key in "${new_keys[@]}"; do
    echo "  + $key=${env_keys[$key]}"
done

if [[ "$DRY_RUN" == "true" ]]; then
    echo ""
    echo "[DRY-RUN] No files modified. Run without --dry-run to apply."
    exit 0
fi

# Append missing keys to target
echo "" >> "$TARGET_FILE"
echo "# --- Merged from $ENV_FILE ---" >> "$TARGET_FILE"
for key in "${new_keys[@]}"; do
    echo "$key=${env_keys[$key]}" >> "$TARGET_FILE"
done
echo "Merged into $TARGET_FILE"

# Backup and symlink
if [[ ! -L "$ENV_FILE" ]]; then
    cp "$ENV_FILE" "${ENV_FILE}.bak"
    rm "$ENV_FILE"
    ln -s "$TARGET_FILE" "$ENV_FILE"
    echo "Backed up to ${ENV_FILE}.bak and symlinked $ENV_FILE -> $TARGET_FILE"
fi

echo "Done. Verify with: grep -c '^[A-Z]' $TARGET_FILE"

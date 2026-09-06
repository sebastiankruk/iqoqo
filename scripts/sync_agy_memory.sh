#!/usr/bin/env bash
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
# sync_agy_memory.sh — Sync Antigravity session transcripts for one version.
#
# Usage: scripts/sync_agy_memory.sh <VERSION>
#   VERSION  iqoqo version string (e.g. 0.7.17)
#
# Single-loop algorithm:
#   1. Walks every transcript_full.jsonl under
#      ~/.gemini/antigravity-{cli,ide}/brain/
#   2. Skips files that do NOT contain VERSION (grep -qF — fast byte scan)
#   3. Converts matching JSONL → Markdown via jq
#   4. Writes output to .context/ai-memory/<VERSION>/<conversation-id>.md
#      (skips when destination is already newer than source)
#
# No intermediate staging directory used.
# Dependencies: jq, bash 4+

set -euo pipefail

VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
    printf 'Usage: %s VERSION\n' "$0" >&2
    exit 1
fi

command -v jq >/dev/null 2>&1 || { echo "sync_agy_memory: jq is required" >&2; exit 1; }

DEST_DIR=".context/ai-memory/${VERSION}"
mkdir -p "$DEST_DIR"

synced=0
skipped_old=0
skipped_no_match=0

for brain_dir in \
    "$HOME/.gemini/antigravity-cli/brain" \
    "$HOME/.gemini/antigravity-ide/brain"; do

    [[ -d "$brain_dir" ]] || continue

    while IFS= read -r -d '' transcript; do
        # Fast version filter — skip sessions that never mention VERSION
        if ! grep -qF "$VERSION" "$transcript" 2>/dev/null; then
            (( skipped_no_match++ )) || true
            continue
        fi

        # Automated task filter — skip background daemon / mykg extraction tasks
        if grep -qF "CRITICAL: Respond ONLY with the requested JSON payload" "$transcript" 2>/dev/null || \
           grep -qF "You are extracting knowledge graph entities and edges for myKG" "$transcript" 2>/dev/null || \
           grep -qF "You are normalizing entity names for myKG" "$transcript" 2>/dev/null || \
           grep -qF "Task: Harmonize and merge concepts" "$transcript" 2>/dev/null || \
           grep -qF "Task: Extract concepts, relationships" "$transcript" 2>/dev/null || \
           grep -qF "Task: Extract concepts, properties" "$transcript" 2>/dev/null || \
           grep -qF "You are an expert ontology engineer" "$transcript" 2>/dev/null; then
            (( skipped_no_match++ )) || true
            continue
        fi

        relative_path="${transcript#"${brain_dir}/"}"
        conversation_id="${relative_path%%/*}"
        dest_file="${DEST_DIR}/${conversation_id}.md"

        # Skip if destination is already up-to-date
        if [[ -e "$dest_file" && ! "$transcript" -nt "$dest_file" ]]; then
            (( skipped_old++ )) || true
            continue
        fi

        if jq -r '
          "## Step \(.step_index) — \(.source) (`\(.type)`) *[\(.created_at)]*\n\n" +
          (if .thinking then "> **Thinking:**\n> " + (.thinking | gsub("\n"; "\n> ")) + "\n\n" else "" end) +
          (if .tool_calls then "```json\n" + (.tool_calls | @json) + "\n```\n\n" else "" end) +
          (if .content then .content + "\n\n" else "" end) +
          "---\n"
        ' "$transcript" > "$dest_file"; then
            printf '%s\n' "$dest_file"
            (( synced++ )) || true
        fi

    done < <(find "$brain_dir" -type f -name 'transcript_full.jsonl' -print0)
done

printf 'sync_agy_memory: synced=%d  skipped_no_match=%d  skipped_up_to_date=%d\n' \
    "$synced" "$skipped_no_match" "$skipped_old"

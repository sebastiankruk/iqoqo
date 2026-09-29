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
#
# MOD-OPS-15: every rendered fragment is passed through `redact_secrets` before
# it is written to disk. Agent transcripts routinely echo back `.env` values,
# Authorization headers and CLI invocations containing tokens; without this
# filter the synced Markdown becomes a plaintext credential store that is then
# indexed into the knowledge graph and committed to the memory repository.

set -euo pipefail

VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
    printf 'Usage: %s VERSION\n' "$0" >&2
    exit 1
fi

command -v jq >/dev/null 2>&1 || { echo "sync_agy_memory: jq is required" >&2; exit 1; }

# Placeholder substituted for every redacted match. It is deliberately not a
# valid value for any credential shape, so a redacted file can never be
# accidentally replayed as a live secret. Passed to jq as --arg rather than
# interpolated into the program text: the regexes below contain both quote
# characters and backslashes, so shell interpolation of the program body is
# error-prone (a stray `'` silently truncates the filter and turns redaction
# into a no-op).
REDACTION='[REDACTED]'

# MOD-OPS-15 redaction filter.
#
# Applied to the fully rendered Markdown (`jq -Rs` slurps the rendered output
# into a single string) so a credential split across two transcript steps is
# still caught and multi-line PEM blocks match.
#
# Patterns, ordered most specific first: the generic assignment rule in 14 would
# otherwise swallow the `sk-…` / `AKIA…` prefix and leave a shortened token
# behind.
#
#   1. PEM private key blocks      8. Slack tokens
#   2. AWS access key IDs          9. JWTs
#   3. Google API keys            10. Fernet keys
#   4. OpenAI-style `sk-` keys    11. HTTP Authorization headers
#   5. GitHub tokens              12. Bearer / Basic payloads
#   6. Anthropic-style keys       13. URL userinfo (scheme://user:pass@host)
#   7. Stripe keys                14. Generic sensitive-name assignments
#
# Constraint: patterns that preserve a prefix use *named* groups only. jq binds
# numbered groups as `\(.N)` and named ones as `\(.name)`, but mixing the two in
# one pattern makes `\(.)` yield the whole match object (verified on jq 1.7),
# which silently corrupts output.
_redact_jq_program=$(cat <<'JQ_REDACT'
def redact:
    # 1. PEM private key blocks (?s enables dot-all inside the group)
    gsub("-----BEGIN [A-Z ]*PRIVATE KEY-----(?s:.*?)-----END [A-Z ]*PRIVATE KEY-----"; $re)
    # 2. AWS access key IDs
  | gsub("AKIA[0-9A-Z]{16}"; $re)
    # 3. Google API keys
  | gsub("AIza[0-9A-Za-z_-]{35}"; $re)
    # 4. OpenAI-style keys
  | gsub("sk-(?:proj-|ant-|live-|test-)?[A-Za-z0-9_-]{16,}"; $re)
    # 5. GitHub tokens
  | gsub("gh[pousr]_[A-Za-z0-9]{20,}"; $re)
  | gsub("github_pat_[A-Za-z0-9_]{20,}"; $re)
    # 6. Anthropic-style keys
  | gsub("sk-ant-[A-Za-z0-9_-]{16,}"; $re)
    # 7. Stripe keys
  | gsub("(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9]{16,}"; $re)
    # 8. Slack tokens
  | gsub("xox[abposr]-[A-Za-z0-9-]{10,}"; $re)
    # 9. JWTs
  | gsub("eyJ[A-Za-z0-9_-]{8,}\\.[A-Za-z0-9_-]{8,}\\.[A-Za-z0-9_-]{8,}"; $re)
    # 10. Fernet keys: 32 bytes base64url-encoded = 43 chars + "=" padding.
  | gsub("\\b[A-Za-z0-9_-]{43}="; $re)
    # 11. Authorization headers: keep the scheme, drop the credential
  | gsub("(?i)(?<pfx>proxy-authorization\"?\\s*[:=]\\s*\"?)[^\\s\"\\\\,;]+"; "\(.pfx)\($re)")
  | gsub("(?i)(?<pfx>authorization\"?\\s*[:=]\\s*\"?)[^\\s\"\\\\,;]+"; "\(.pfx)\($re)")
    # 12. Bearer / Basic payloads
  | gsub("(?i)(?<pfx>bearer\\s+)[A-Za-z0-9._~+/=-]{8,}"; "\(.pfx)\($re)")
  | gsub("(?i)(?<pfx>basic\\s+)[A-Za-z0-9+/=]{8,}"; "\(.pfx)\($re)")
    # 13. URL userinfo: scheme://user:password@host
  | gsub("(?<scheme>[a-zA-Z][a-zA-Z0-9+.-]*://)(?<user>[^:/@\\s]+):(?<pw>[^@/\\s]+)@"; "\(.scheme)\(.user):\($re)@")
    # 14. Generic sensitive-name assignments (env, JSON, YAML, CLI flags).
  | gsub("(?i)(?<k>[A-Z0-9_.-]*(?:SECRET|PASSWORD|PASSWD|API_?KEY|TOKEN|CREDENTIALS?|PRIVATE_KEY|SALT|DSN|BASIC_AUTH)[A-Z0-9_.-]*\"?\\s*[:=]\\s*\"?)[^\\s\"',;&)]+"; "\(.k)\($re)")
  ;
redact
JQ_REDACT
)

# Fail closed: prove the redaction filter actually fires on this jq build before
# writing anything. A silent no-op filter is worse than no filter at all, because
# the operator would believe the output had been scrubbed.
_redact_probe=$(printf '%s\n' \
    'SECRET_KEY="notarealsecretbutlongenough" AKIAIOSFODNN7EXAMPLE' \
    | jq -rRs --arg re "$REDACTION" "$_redact_jq_program" 2>/dev/null || true)
if ! grep -qF "$REDACTION" <<<"$_redact_probe" \
   || grep -qE 'notarealsecretbutlongenough|AKIAIOSFODNN7EXAMPLE' <<<"$_redact_probe"; then
    echo "sync_agy_memory: secret redaction unavailable in this jq build; refusing to sync." >&2
    exit 1
fi

# Only now, with redaction proven to work, create the destination directory.
DEST_DIR=".context/ai-memory/${VERSION}"
mkdir -p "$DEST_DIR"

synced=0
skipped_old=0
skipped_no_match=0
redacted_files=0

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

        # Render the transcript to Markdown, then scrub it. `-Rs` slurps the
        # whole rendered document into a single string before running the
        # redaction filter, so credentials split across render steps and
        # multi-line PEM blocks are still matched. The raw render goes to a
        # temp file that is removed on every exit path — an unscrubbed copy
        # must never survive on disk.
        raw_file=$(mktemp "${TMPDIR:-/tmp}/agy_render.XXXXXX")
        chmod 0600 "$raw_file"
        if jq -r '
          "## Step \(.step_index) — \(.source) (`\(.type)`) *[\(.created_at)]*\n\n" +
          (if .thinking then "> **Thinking:**\n> " + (.thinking | gsub("\n"; "\n> ")) + "\n\n" else "" end) +
          (if .tool_calls then "```json\n" + (.tool_calls | @json) + "\n```\n\n" else "" end) +
          (if .content then .content + "\n\n" else "" end) +
          "---\n"
        ' "$transcript" > "$raw_file" \
           && jq -rRs --arg re "$REDACTION" "$_redact_jq_program" "$raw_file" > "$dest_file"; then
            if ! cmp -s "$raw_file" "$dest_file"; then
                (( redacted_files++ )) || true
            fi
            printf '%s\n' "$dest_file"
            (( synced++ )) || true
        else
            echo "sync_agy_memory: failed to render $transcript" >&2
        fi
        rm -f "$raw_file"

    done < <(find "$brain_dir" -type f -name 'transcript_full.jsonl' -print0)
done

printf 'sync_agy_memory: synced=%d  redacted=%d  skipped_no_match=%d  skipped_up_to_date=%d\n' \
    "$synced" "$redacted_files" "$skipped_no_match" "$skipped_old"

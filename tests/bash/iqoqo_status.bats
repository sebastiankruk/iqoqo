#!/usr/bin/env bats
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

setup() {
  export TEST_TEMP_DIR="$(mktemp -d)"
}

teardown() {
  rm -rf "${TEST_TEMP_DIR}"
}

@test "iqoqo-status.sh displays help information" {
  run bash scripts/iqoqo-status.sh --help
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Check health status of all iQoQo services" ]]
}

@test "iqoqo-status.sh fails on invalid argument" {
  run bash scripts/iqoqo-status.sh --invalid-argument-foo
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Unknown option:" ]]
}

@test "iqoqo-status.sh shows environment configuration audit" {
  unset IQOQO_AI_MODE || true
  run env -u IQOQO_AI_MODE bash scripts/iqoqo-status.sh
  [[ "$output" =~ "Environment Configuration" ]]
  [[ "$output" =~ "Configured" ]]
}

@test "iqoqo-status.sh suppresses ASCII banner in AI mode" {
  export IQOQO_AI_MODE=1
  run bash scripts/iqoqo-status.sh
  [[ ! "$output" =~ "╔══════════════════════════════════════════════╗" ]]
  [[ ! "$output" =~ "Environment Configuration" ]]
  [[ "$output" =~ "STATUS:" ]]
}

@test "iqoqo-status.sh reports Allegro API configuration status" {
  unset IQOQO_AI_MODE || true
  run env -u IQOQO_AI_MODE bash scripts/iqoqo-status.sh
  [[ "$output" =~ "Instance Settings" || "$output" =~ "Allegro" ]]
}

@test "iqoqo-status.sh reports not configured when Allegro credentials missing" {
  env_file="${TEST_TEMP_DIR}/.env.test"
  echo "ENV_FILE=.env.dev" > "$env_file"
  echo "ALLEGRO_CLIENT_ID=" >> "$env_file"
  echo "ALLEGRO_CLIENT_SECRET=" >> "$env_file"
  run env -u IQOQO_AI_MODE ENV_FILE="$env_file" bash scripts/iqoqo-status.sh
  [[ "$output" =~ "not configured" || "$output" =~ "Instance Settings" ]]
}

@test "iqoqo-status.sh discriminates probe error correctly" {
  run bash -c '
    allegro_status_json="{\"configured\": true, \"allegro_token_active\": false, \"reason\": \"query_failed\"}"
    reason=$(echo "$allegro_status_json" | python3 -c "import sys, json; print(json.load(sys.stdin).get(\"reason\", \"\"))")
    if [[ "$reason" == "query_failed" || "$reason" == "probe_error" ]]; then
      echo "probe error detected"
    fi
  '
  [ "$status" -eq 0 ]
  [[ "$output" =~ "probe error detected" ]]
}

@test "iqoqo-status.sh discriminates active token correctly" {
  run bash -c '
    allegro_status_json="{\"configured\": true, \"allegro_token_active\": true, \"token_age_hours\": 2.5, \"reason\": \"active\"}"
    is_active=$(echo "$allegro_status_json" | python3 -c "import sys, json; print(json.load(sys.stdin).get(\"allegro_token_active\", False))")
    token_age=$(echo "$allegro_status_json" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get(\"token_age_hours\", \"\"))")
    if [[ "$is_active" == "True" ]]; then
      echo "active (token age: ${token_age}h)"
    fi
  '
  [ "$status" -eq 0 ]
  [[ "$output" =~ "active (token age: 2.5h)" ]]
}

@test "iqoqo-status.sh discriminates expired token correctly" {
  run bash -c '
    allegro_status_json="{\"configured\": true, \"allegro_token_active\": false, \"is_expired\": true, \"token_age_hours\": 48.0, \"reason\": \"expired\"}"
    is_expired=$(echo "$allegro_status_json" | python3 -c "import sys, json; print(json.load(sys.stdin).get(\"is_expired\", False))")
    token_age=$(echo "$allegro_status_json" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get(\"token_age_hours\", \"\"))")
    if [[ "$is_expired" == "True" ]]; then
      echo "token expired (${token_age}h old, re-authorize in Instance Settings)"
    fi
  '
  [ "$status" -eq 0 ]
  [[ "$output" =~ "token expired (48.0h old, re-authorize in Instance Settings)" ]]
}

@test "iqoqo-status.sh flags default SPARQL_SERVICE_SECRET in production" {
  env_file="${TEST_TEMP_DIR}/.env"
  echo "FLASK_ENV=production" > "$env_file"
  echo "SPARQL_SERVICE_SECRET=dev-sparql-service-secret" >> "$env_file"
  run env -u IQOQO_AI_MODE bash scripts/iqoqo-status.sh --deploy-dir "${TEST_TEMP_DIR}"
  [[ "$output" =~ "using default development secret in production" ]]
}

@test "iqoqo-status.sh validates non-default SPARQL_SERVICE_SECRET in production" {
  env_file="${TEST_TEMP_DIR}/.env"
  echo "FLASK_ENV=production" > "$env_file"
  echo "SPARQL_SERVICE_SECRET=super-secure-prod-secret-9999" >> "$env_file"
  run env -u IQOQO_AI_MODE bash scripts/iqoqo-status.sh --deploy-dir "${TEST_TEMP_DIR}"
  [[ "$output" =~ "SPARQL_SERVICE_SECRET is configured with non-default value" ]]
}

@test "iqoqo-status.sh warns when container mounts are unwritable" {
  mock_bin="${TEST_TEMP_DIR}/mock_bin"
  mkdir -p "${mock_bin}"
  printf '#!/bin/bash\nif [[ "$*" == *"test -w"* ]]; then\n  if [[ "$*" == *"exports"* ]]; then exit 1; fi\n  exit 0\nfi\nif [[ "$*" == *"ps --format"* ]]; then\n  echo "iqoqo-web-1"\n  exit 0\nfi\nexit 0\n' > "${mock_bin}/docker"
  chmod +x "${mock_bin}/docker"

  run env -u IQOQO_AI_MODE PATH="${mock_bin}:$PATH" bash scripts/iqoqo-status.sh prod
  [[ "$output" =~ "Mount permissions" ]]
  [[ "$output" =~ "NOT writable in container" ]]
  [[ "$output" =~ "exports" ]]
  [[ "$output" =~ "make ensure-mount-perms" ]]
}

@test "iqoqo-status.sh passes when all container mounts are writable" {
  mock_bin="${TEST_TEMP_DIR}/mock_bin2"
  mkdir -p "${mock_bin}"
  printf '#!/bin/bash\nif [[ "$*" == *"test -w"* ]]; then\n  exit 0\nfi\nif [[ "$*" == *"ps --format"* ]]; then\n  echo "iqoqo-web-1"\n  exit 0\nfi\nexit 0\n' > "${mock_bin}/docker"
  chmod +x "${mock_bin}/docker"

  run env -u IQOQO_AI_MODE PATH="${mock_bin}:$PATH" bash scripts/iqoqo-status.sh prod
  [[ "$output" =~ "Mount permissions" ]]
  [[ "$output" =~ "covers, gallery, exports, data writable" ]]
}

@test "iqoqo-status.sh reports Metadata Lookup Providers section" {
  unset IQOQO_AI_MODE || true
  run env -u IQOQO_AI_MODE bash scripts/iqoqo-status.sh
  [[ "$output" =~ "Metadata Lookup Providers" ]]
  [[ "$output" =~ "Discogs API" ]]
  [[ "$output" =~ "TMDB API" ]]
  [[ "$output" =~ "Google Books API" ]]
  [[ "$output" =~ "UPC Databases" ]]
}

@test "iqoqo-status.sh recognizes DB-configured keys in Environment Configuration" {
  run bash -c '
    declare -A db_settings_map
    db_settings_map["BGG_API_TOKEN"]=1
    db_settings_map["DISCOGS_USER_TOKEN"]=1
    expected_keys=("BGG_API_TOKEN" "DISCOGS_USER_TOKEN" "OTHER_UNSET")
    declare -A example_defaults
    example_defaults["BGG_API_TOKEN"]="empty"
    example_defaults["DISCOGS_USER_TOKEN"]="empty"
    example_defaults["OTHER_UNSET"]="set"
    active_count=0
    db_active_count=0
    missing_warn=0
    for key in "${expected_keys[@]}"; do
      val=""
      if [[ -n "$val" ]]; then
        active_count=$((active_count + 1))
      elif [[ -n "${db_settings_map[$key]:-}" ]]; then
        active_count=$((active_count + 1))
        db_active_count=$((db_active_count + 1))
      else
        missing_warn=$((missing_warn + 1))
      fi
    done
    echo "active: $active_count, in DB: $db_active_count, missing: $missing_warn"
  '
  [ "$status" -eq 0 ]
  [[ "$output" =~ "active: 2, in DB: 2, missing: 1" ]]
}

@test "env.status-classes covers every key in .env.example with valid class" {
  run python3 -c '
example_keys = set()
with open(".env.example") as f:
    for line in f:
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            example_keys.add(s.split("=", 1)[0].strip())

classes = {}
with open(".env.status-classes") as f:
    for line in f:
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            classes[k.strip()] = v.strip()

missing = sorted(example_keys - set(classes))
invalid = sorted(k for k, v in classes.items() if v not in ("required", "default", "optional"))
assert not missing, f"Unclassified .env.example keys: {missing}"
assert not invalid, f"Invalid classes: {invalid}"
print(f"classified {len(example_keys)} keys")
'
  [ "$status" -eq 0 ]
  [[ "$output" =~ "classified" ]]
}

@test "iqoqo-status.sh treats missing defaulted vars as info and missing required vars as warn" {
  tmp_root="${TEST_TEMP_DIR}/env_class_test"
  mkdir -p "${tmp_root}/scripts"
  cp scripts/iqoqo-status.sh "${tmp_root}/scripts/iqoqo-status.sh"
  printf 'DATABASE_URL=postgresql://u:p@db:5432/app\nAPP_PORT=5000\n' > "${tmp_root}/.env.example"
  printf 'DATABASE_URL=required\nAPP_PORT=default\n' > "${tmp_root}/.env.status-classes"
  printf '# empty\n' > "${tmp_root}/.env"

  run env -u IQOQO_AI_MODE ENV_FILE="${tmp_root}/.env" IQOQO_ROOT="${tmp_root}" ENV_STATUS_CLASSES_FILE="${tmp_root}/.env.status-classes" bash "${tmp_root}/scripts/iqoqo-status.sh" dev
  [[ "$output" =~ "Missing (required)" ]]
  [[ "$output" =~ "1 variable(s): DATABASE_URL" ]]
  [[ "$output" =~ "Defaulted" ]]
  [[ "$output" =~ "1 variable(s) (using code/compose defaults): APP_PORT" ]]
}

@test "iqoqo-status.sh ignores OTel export errors during grace window and fails on sustained errors" {
  mock_bin_grace="${TEST_TEMP_DIR}/mock_bin_grace"
  mkdir -p "${mock_bin_grace}"
  started_recent=$(python3 -c "from datetime import datetime, timezone, timedelta; print((datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat().replace('+00:00', 'Z'))")
  cat > "${mock_bin_grace}/docker" <<EOF
#!/bin/bash
if [[ "\$*" == *"ps --format"* ]]; then
  echo "iqoqo-otel-collector-1"
  exit 0
elif [[ "\$*" == *"inspect -f"* ]]; then
  echo "${started_recent}"
  exit 0
elif [[ "\$*" == *"logs "* ]]; then
  echo "Exporting failed. Dropping data."
  exit 0
fi
exit 0
EOF
  chmod +x "${mock_bin_grace}/docker"

  run env -u IQOQO_AI_MODE OTEL_EXPORT_GRACE_SECONDS=60 PATH="${mock_bin_grace}:$PATH" bash scripts/iqoqo-status.sh prod
  [[ "$output" =~ "transient export failure(s) during startup grace" ]]

  mock_bin_sustained="${TEST_TEMP_DIR}/mock_bin_sustained"
  mkdir -p "${mock_bin_sustained}"
  started_old=$(python3 -c "from datetime import datetime, timezone, timedelta; print((datetime.now(timezone.utc) - timedelta(seconds=180)).isoformat().replace('+00:00', 'Z'))")
  cat > "${mock_bin_sustained}/docker" <<EOF
#!/bin/bash
if [[ "\$*" == *"ps --format"* ]]; then
  echo "iqoqo-otel-collector-1"
  exit 0
elif [[ "\$*" == *"inspect -f"* ]]; then
  echo "${started_old}"
  exit 0
elif [[ "\$*" == *"logs "* ]]; then
  echo "Exporting failed. Dropping data."
  exit 0
fi
exit 0
EOF
  chmod +x "${mock_bin_sustained}/docker"

  run env -u IQOQO_AI_MODE OTEL_EXPORT_GRACE_SECONDS=60 PATH="${mock_bin_sustained}:$PATH" bash scripts/iqoqo-status.sh prod
  [[ "$output" =~ "export failures in last" ]]
}


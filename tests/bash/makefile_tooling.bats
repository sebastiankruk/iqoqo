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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# tests/bash/makefile_tooling.bats
# Tests for Makefile targets related to tooling scripts.

@test "Makefile has fix-physical-kinds target" {
  run grep -E '^fix-physical-kinds:' Makefile
  [ "$status" -eq 0 ]
}

@test "Makefile fix-physical-kinds target invokes fix_physical_kinds.py" {
  run make -n fix-physical-kinds
  [ "$status" -eq 0 ]
  [[ "$output" == *"fix_physical_kinds.py"* ]]
}

@test "Makefile has refetch-metadata target" {
  run grep -E '^refetch-metadata:' Makefile
  [ "$status" -eq 0 ]
}

@test "Makefile refetch-metadata target invokes refetch_metadata.py" {
  run make -n refetch-metadata
  [ "$status" -eq 0 ]
  [[ "$output" == *"refetch_metadata.py"* ]]
}

@test "Makefile fix-physical-kinds target passes ARGS" {
  run make -n fix-physical-kinds ARGS="--audit"
  [ "$status" -eq 0 ]
  [[ "$output" == *"--audit"* ]]
}

@test "Makefile refetch-metadata dry-run flag passed" {
  run make -n refetch-metadata dry-run=true
  [ "$status" -eq 0 ]
  [[ "$output" == *"--dry-run"* ]]
}

@test "Makefile refetch-metadata force flag passed" {
  run make -n refetch-metadata force=true
  [ "$status" -eq 0 ]
  [[ "$output" == *"--force"* ]]
}

@test "Makefile refetch-metadata limit flag passed" {
  run make -n refetch-metadata limit=10
  [ "$status" -eq 0 ]
  [[ "$output" == *"--limit"* ]]
  [[ "$output" == *"10"* ]]
}

@test "Makefile fix-physical-kinds apply and dry-run flags passed" {
  run make -n fix-physical-kinds ARGS="--apply --dry-run"
  [ "$status" -eq 0 ]
  [[ "$output" == *"--apply"* ]]
  [[ "$output" == *"--dry-run"* ]]
}

@test "Makefile fix-physical-kinds interactive flag passed" {
  run make -n fix-physical-kinds ARGS="--interactive"
  [ "$status" -eq 0 ]
  [[ "$output" == *"--interactive"* ]]
}

@test "Makefile lint-python in standard mode outputs echo commands" {
  run env -u IQOQO_AI_MODE make -n lint-python IQOQO_AI_MODE=
  [ "$status" -eq 0 ]
  [[ "$output" == *"echo \"Running ruff...\""* ]]
  [[ "$output" == *"echo \"Running mypy...\""* ]]
  [[ "$output" == *"echo \"Running pylint...\""* ]]
}

@test "Makefile lint-python in AI mode suppresses echo commands and adds terse flags" {
  run make -n lint-python IQOQO_AI_MODE=1
  [ "$status" -eq 0 ]
  [[ "$output" != *"echo \"Running ruff...\""* ]]
  [[ "$output" == *"--output-format=concise"* ]]
  [[ "$output" == *"--no-error-summary"* ]]
  [[ "$output" == *"--msg-template="* ]]
}

@test "Makefile test-backend in AI mode suppresses echo commands" {
  run make -n test-backend IQOQO_AI_MODE=1
  [ "$status" -eq 0 ]
  [[ "$output" != *"echo \"Running backend tests...\""* ]]
  [[ "$output" == *"-q --tb=short --no-header"* ]]
}

@test "Makefile test-backend-pg in AI mode suppresses verbose flags and echo" {
  run make -n test-backend-pg IQOQO_AI_MODE=1
  [ "$status" -eq 0 ]
  [[ "$output" != *"echo \"Running PostgreSQL-dependent"* ]]
  [[ "$output" == *"-q --tb=short --no-header"* ]]
  [[ "$output" != *"pytest tests/integration/db/ -v"* ]]
}

@test "Makefile test-scripts-python includes tests/scripts/ and AI flags" {
  run make -n test-scripts-python IQOQO_AI_MODE=1
  [ "$status" -eq 0 ]
  [[ "$output" == *"tests/scripts/"* ]]
  [[ "$output" == *"-q --tb=short --no-header"* ]]
}

@test "Makefile test-frontend in AI mode passes --reporter=dot" {
  run make -n test-frontend IQOQO_AI_MODE=1
  [ "$status" -eq 0 ]
  [[ "$output" == *"--reporter=dot"* ]]
  [[ "$output" != *"echo \"Running frontend unit tests"* ]]
}

@test "Makefile test-scripts-bash in AI mode pipes TAP output to format_bats_ai.py" {
  run make -n test-scripts-bash IQOQO_AI_MODE=1
  [ "$status" -eq 0 ]
  [[ "$output" == *"--formatter tap"* ]]
  [[ "$output" == *"format_bats_ai.py"* ]]
}

@test "Makefile test-e2e-federation dry-run does not execute live containers" {
  run make -n test-e2e-federation IQOQO_AI_MODE=1
  [ "$status" -eq 0 ]
  [[ "$output" == *"federated_friend_request.spec.ts"* ]]
  [[ "$output" != *"help_hub_workflow.spec.ts"* ]]
}

@test "Makefile status can retrieve the helper from the preview backend image" {
  run make -n status STACK=preview
  [ "$status" -eq 0 ]
  [[ "$output" == *"docker compose -p \"iqoqo-preview\""* ]]
  [[ "$output" == *"ps --all -q web"* ]]
  [[ "$output" == *"config --format json"* ]]
  [[ "$output" == *"/usr/src/app/scripts/iqoqo-status.sh"* ]]
  [[ "$output" == *"IQOQO_STATUS_ROOT"* ]]
}

@test "status helper accepts an explicit host deployment root" {
  run grep -F 'IQOQO_ROOT="${IQOQO_STATUS_ROOT:-' scripts/iqoqo-status.sh
  [ "$status" -eq 0 ]
}


@test "Makefile status fallback passes --deploy-dir for preview" {
  run make -n status STACK=preview
  [ "$status" -eq 0 ]
  [[ "$output" == *"--deploy-dir"* ]]
}

@test "Makefile monitoring-reset-auth pipes OPENOBSERVE_BASIC_AUTH via stdin instead of -e argv" {
  run make -n monitoring-reset-auth MODE=preview
  [ "$status" -eq 0 ]
  [[ "$output" != *"-e OO_BASIC_AUTH"* ]]
  [[ "$output" == *"sys.stdin.read().strip()"* ]]
}

@test "Makefile monitoring-reset-auth uses --project-directory and --force-recreate --no-deps" {
  run make -n monitoring-reset-auth MODE=preview
  [ "$status" -eq 0 ]
  [[ "$output" == *"--project-directory"* ]]
  [[ "$output" == *"--enforce-openobserve-password-policy"* ]]
  [[ "$output" == *"up -d --force-recreate --no-deps openobserve otel-collector"* ]]
  [[ "$output" == *"up -d --force-recreate --no-deps web worker frontend"* ]]
}

@test "Makefile has preview-reconcile target" {
  run grep -E '^preview-reconcile:' Makefile
  [ "$status" -eq 0 ]
}

@test "Makefile preview-reconcile defaults SKIP_CLONE to 0, frames stdin, runs RUM in container, and preserves running tag" {
  run make -n preview-reconcile DEPLOY_DIR="${BATS_TEST_TMPDIR}/nonexistent-deploy"
  [ "$status" -eq 0 ]
  [[ "$output" == *'SKIP_CLONE:-0'* ]]
  [[ "$output" == *"__IQOQO_SRC_SECRET_KEY__="* ]]
  [[ "$output" == *"reconcile_preview_settings.py --dotenv-stdin"* ]]
  [[ "$output" == *"exec -T web env PYTHONPATH=/usr/src/app python3 /usr/src/app/scripts/provision_rum_token.py --mgmt-host openobserve"* ]]
  [[ "$output" != *'APP_VERSION=${APP_VERSION:-preview}'* ]]
  [[ "$output" == *'eff_app_ver="${eff_app_ver:-'* ]]
}

@test "Makefile monitoring-reset-auth resolves running web image APP_VERSION before recreate" {
  run make -n monitoring-reset-auth MODE=preview
  [ "$status" -eq 0 ]
  [[ "$output" == *'eff_app_ver="${eff_app_ver:-'* ]]
  [[ "$output" == *'APP_VERSION="$eff_app_ver" docker compose'* ]]
}

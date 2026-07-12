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

# tests/bash/scripts_syntax.bats
# Validates syntax of all bash scripts in scripts/ directory.

@test "scripts/check_license.sh syntax check" {
  run bash -n scripts/check_license.sh
  [ "$status" -eq 0 ]
}

@test "scripts/clone.sh syntax check" {
  run bash -n scripts/clone.sh
  [ "$status" -eq 0 ]
}

@test "scripts/cloud_backup.sh syntax check" {
  run bash -n scripts/cloud_backup.sh
  [ "$status" -eq 0 ]
}

@test "scripts/cloud_backup_check.sh syntax check" {
  run bash -n scripts/cloud_backup_check.sh
  [ "$status" -eq 0 ]
}

@test "scripts/cloud_backup_cron.sh syntax check" {
  run bash -n scripts/cloud_backup_cron.sh
  [ "$status" -eq 0 ]
}

@test "scripts/import_covers.sh syntax check" {
  run bash -n scripts/import_covers.sh
  [ "$status" -eq 0 ]
}

@test "scripts/iqoqo-status.sh syntax check" {
  run bash -n scripts/iqoqo-status.sh
  [ "$status" -eq 0 ]
}

@test "scripts/setup_db.sh syntax check" {
  run bash -n scripts/setup_db.sh
  [ "$status" -eq 0 ]
}

@test "scripts/test_docker_builds.sh syntax check" {
  run bash -n scripts/test_docker_builds.sh
  [ "$status" -eq 0 ]
}

@test "scripts/allegro_auth.sh syntax check" {
  run bash -n scripts/allegro_auth.sh
  [ "$status" -eq 0 ]
}

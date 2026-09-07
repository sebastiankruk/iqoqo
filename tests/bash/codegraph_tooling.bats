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

@test "Makefile has codegraph targets" {
  run make -n codegraph-sync
  [ "$status" -eq 0 ]
  [[ "$output" == *"codegraph sync"* ]]

  run make -n codegraph-status
  [ "$status" -eq 0 ]
  [[ "$output" == *"codegraph status"* ]]
}

@test "Makefile codegraph-sync executes successfully when CLI installed" {
  if ! command -v codegraph >/dev/null 2>&1; then
    skip "codegraph CLI not installed in environment"
  fi
  run make codegraph-sync
  [ "$status" -eq 0 ]
  [[ "$output" == *"Syncing CodeGraph"* || "$output" == *"Already up to date"* ]]
}

@test "Makefile codegraph-status displays index statistics when CLI installed" {
  if ! command -v codegraph >/dev/null 2>&1; then
    skip "codegraph CLI not installed in environment"
  fi
  run make codegraph-status
  [ "$status" -eq 0 ]
  [[ "$output" == *"CodeGraph Status"* ]]
  [[ "$output" == *"Index Statistics:"* ]]
}

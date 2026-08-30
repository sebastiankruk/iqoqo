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

@test "Makefile mempalace-scope executes successfully" {
  run make mempalace-scope
  [ "$status" -eq 0 ]
  [[ "$output" == *"iQoQo MemPalace Scopes Discovered"* ]]
  [[ "$output" == *"Target Wing: iqoqo"* ]]
}

@test "Makefile mempalace-index dry-run runs correctly" {
  run make mempalace-index ARGS="--dry-run"
  [ "$status" -eq 0 ]
  [[ "$output" == *"Starting iQoQo Scoped MemPalace Mining"* ]]
}

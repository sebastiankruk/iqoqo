#!/bin/bash
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

gh api /repos/sebastiankruk/iqoqo/dependabot/alerts \
  --jq '.[] | {
    number:                   .number,
    state:                    .state,
    severity:                 .security_advisory.severity,
    summary:                  .security_advisory.summary,
    package:                  .dependency.package.name,
    ecosystem:                .dependency.package.ecosystem,
    vulnerable_version_range: .security_vulnerability.vulnerable_version_range,
    patched_versions:         .security_vulnerability.first_patched_version.identifier,
    manifest_path:            .dependency.manifest_path
  }' \
  2>&1 > .alerts.json

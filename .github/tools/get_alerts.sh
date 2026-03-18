#!/bin/bash

gh api /repos/sebastiankruk/iqoqo/dependabot/alerts --jq '.[] | {number: .number, state: .state, severity: .security_advisory.severity, summary: .security_advisory.summary, package: .dependency.package.name, ecosystem: .dependency.package.ecosystem, vulnerable_version_range: .security_vulnerability.vulnerable_version_range, patched_versions: .security_vulnerability.first_patched_version.identifier, manifest_path: .dependency.manifest_path}' 2>&1 > .alerts.json

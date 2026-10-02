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
  export PATH="${TEST_TEMP_DIR}/stub-bin:${PATH}"
  mkdir -p "${TEST_TEMP_DIR}/stub-bin"

  # Stub sudo to bypass and just execute the command directly
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/sudo"
#!/bin/bash
exec "$@"
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/sudo"

  # Stub docker
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/docker"
#!/bin/bash
# Just succeed on cp, exec, etc.
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/docker"
}

teardown() {
  rm -rf "${TEST_TEMP_DIR}"
}

@test "import_covers.sh exits 1 if archive does not exist" {
  run bash scripts/import_covers.sh my-container "/nonexistent/path/covers.tar.gz"
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Error: Archive not found" ]]
}

# A real gzip archive. The two happy-path tests previously used `touch`, which
# produces a zero-byte file -- not a gzip archive at all. They passed only
# because nothing validated the input, so they asserted nothing about success.
make_valid_archive() {
  local outfile="$1"
  local staging
  staging="$(mktemp -d)"
  mkdir -p "${staging}/covers"
  : > "${staging}/covers/manifestation_1_cover.jpg"
  tar -czf "${outfile}" -C "${staging}" covers
  rm -rf "${staging}"
}

@test "import_covers.sh exits 1 if archive is not a readable gzip" {
  local archive="${TEST_TEMP_DIR}/covers.tar.gz"
  printf 'this is not a gzip stream' > "${archive}"

  run bash scripts/import_covers.sh test-container "${archive}"
  [ "$status" -eq 1 ]
  [[ "$output" =~ "not a readable gzip archive" ]]
}

@test "import_covers.sh exits 1 on a truncated archive and does not reach the container" {
  local archive="${TEST_TEMP_DIR}/covers.tar.gz"
  make_valid_archive "${archive}"
  # Truncate the way an interrupted upload does. Appending garbage would NOT
  # work: gzip ignores trailing bytes after the last member, so the archive
  # still lists fine and only fails once extraction reaches the end.
  truncate -s -24 "${archive}"

  # Record whether the container was touched at all.
  local marker="${TEST_TEMP_DIR}/docker-was-called"
  cat << EOF > "${TEST_TEMP_DIR}/stub-bin/docker"
#!/bin/bash
touch "${marker}"
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/docker"

  run bash scripts/import_covers.sh test-container "${archive}"
  [ "$status" -eq 1 ]
  [[ "$output" =~ "not a readable gzip archive" ]]
  if [ -f "${marker}" ]; then
    echo "the archive was pushed into the container despite being unreadable" >&2
    return 1
  fi
}

@test "import_covers.sh runs successfully when archive exists and user declines deletion" {
  local archive="${TEST_TEMP_DIR}/covers.tar.gz"
  make_valid_archive "${archive}"

  # Pipe 'n' to answer the delete prompt
  run bash -c "echo 'n' | bash scripts/import_covers.sh test-container ${archive}"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Import complete!" ]]
  [[ "$output" =~ "Archive kept on host" ]]
  [ -f "${archive}" ]
}

@test "import_covers.sh runs successfully and deletes archive when user accepts" {
  local archive="${TEST_TEMP_DIR}/covers.tar.gz"
  make_valid_archive "${archive}"

  # Pipe 'y' to answer the delete prompt
  run bash -c "echo 'y' | bash scripts/import_covers.sh test-container ${archive}"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Import complete!" ]]
  # The file should be deleted
  [ ! -f "${archive}" ]
}

@test "import_covers.sh aborts when extraction fails inside the container" {
  local archive="${TEST_TEMP_DIR}/covers.tar.gz"
  make_valid_archive "${archive}"

  # Docker succeeds for `cp`, fails for the extraction `exec`, succeeds after.
  cat << 'EOF' > "${TEST_TEMP_DIR}/stub-bin/docker"
#!/bin/bash
case "$*" in
  *"tar -xzvf"*) echo "tar: Unexpected EOF in archive" >&2; exit 2 ;;
  *) exit 0 ;;
esac
EOF
  chmod +x "${TEST_TEMP_DIR}/stub-bin/docker"

  run bash -c "echo 'n' | bash scripts/import_covers.sh test-container ${archive}"
  [ "$status" -eq 1 ]
  [[ "$output" =~ "extraction failed" ]]
  [[ "$output" =~ "Rebinding was NOT run" ]]
  [[ "$output" != *"Import complete!" ]]
}

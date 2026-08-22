#!/bin/sh
# test_docker_entrypoint.sh
# Tests that docker-entrypoint.sh does not crash when HOME is read-only.

set -e

echo "Running docker-entrypoint.sh regression test..."

# 1. Setup a fake read-only HOME directory
TMP_HOME=$(mktemp -d)
mkdir -p "$TMP_HOME/.config/rclone"
# Make it read-only
chmod 0555 "$TMP_HOME"
chmod 0555 "$TMP_HOME/.config"
chmod 0555 "$TMP_HOME/.config/rclone"

# 2. Run the entrypoint script, simulating container start
# We pass "true" as the command for the entrypoint to exec.
export HOME="$TMP_HOME"
if ! ./deploy/docker-entrypoint.sh true; then
    echo "FAIL: docker-entrypoint.sh crashed on read-only HOME."
    chmod 0755 "$TMP_HOME" -R || true
    rm -rf "$TMP_HOME"
    exit 1
fi

echo "SUCCESS: docker-entrypoint.sh completed without crashing."

# Cleanup
chmod 0755 "$TMP_HOME" -R || true
rm -rf "$TMP_HOME"
exit 0

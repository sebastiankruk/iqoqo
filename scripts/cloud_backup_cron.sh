#!/bin/bash
# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# iQoQo Cloud Backup Cron Management
# Usage: ./scripts/cloud_backup_cron.sh install <remote>
#        ./scripts/cloud_backup_cron.sh uninstall

set -euo pipefail

CMD="${1:-}"
REMOTE="${2:-iqoqo-backup}"

case "${CMD}" in
  install)
    if ! rclone listremotes 2>/dev/null | grep -q "^${REMOTE}:"; then
      echo "ERROR: Remote '${REMOTE}' not found" >&2
      exit 1
    fi
    echo "Installing daily 03:00 cron job for remote '${REMOTE}'..."
    PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
    echo "0 3 * * * root cd ${PROJECT_DIR} && RCLONE_CONFIG=${HOME}/.config/rclone/rclone.conf ./scripts/cloud_backup.sh ${REMOTE} >> /var/log/iqoqo_backup.log 2>&1" | \
      docker run --rm -i -v /etc/cron.d:/etc/cron.d --entrypoint sh alpine -c 'cat > /etc/cron.d/iqoqo-backup'
    echo "Done. Next run: tonight at 03:00."
    ;;
  uninstall)
    echo "Removing iQoQo backup cron job..."
    docker run --rm -v /etc/cron.d:/etc/cron.d --entrypoint sh alpine -c 'rm -f /etc/cron.d/iqoqo-backup'
    echo "Done."
    ;;
  *)
    echo "Usage: $0 <install|uninstall> [remote]" >&2
    echo "  install <remote>   - Install daily 03:00 cron job" >&2
    echo "  uninstall          - Remove cron job" >&2
    exit 1
    ;;
esac
#!/bin/sh
# docker-entrypoint.sh
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
# Container entrypoint: pre-start checks executed before any application
# command (gunicorn, celery, or ad-hoc `docker run ... <cmd>`).

set -e

# Pre-start check: ensure the rclone configuration directory exists.
# In-container backup and cover-cache jobs invoke rclone as the runtime
# user; on fresh deployments without a host bind-mount of the config,
# ${HOME}/.config/rclone is missing and rclone fails silently.
# `mkdir -p` is idempotent: a no-op when the directory (or bind-mount)
# already exists, so this is safe to run on every container start.
mkdir -p "${HOME}/.config/rclone" 2>/dev/null || true
chmod 0700 "${HOME}/.config/rclone" 2>/dev/null || true
RCLONE_CONF="${HOME}/.config/rclone/rclone.conf"
if [ -e "${RCLONE_CONF}" ]; then
  chmod 0600 "${RCLONE_CONF}" 2>/dev/null || true
  if [ ! -r "${RCLONE_CONF}" ]; then
    echo "WARNING: ${RCLONE_CONF} exists but is not readable by UID $(id -u). Cloud backup and restore jobs may fail. Check host file permissions (recommend chmod 0640 or chown UID 10001)." >&2
  fi
fi

# Auto-rewrite localhost database and redis URLs to docker service names
if [ -n "$DATABASE_URL" ]; then
  case "$DATABASE_URL" in
    *@localhost:*)
      export DATABASE_URL=$(echo "$DATABASE_URL" | sed 's/@localhost:/@db:/')
      ;;
    *@127.0.0.1:*)
      export DATABASE_URL=$(echo "$DATABASE_URL" | sed 's/@127.0.0.1:/@db:/')
      ;;
    *//localhost:*)
      export DATABASE_URL=$(echo "$DATABASE_URL" | sed 's/\/\/localhost:/\/\/db:/')
      ;;
    *//127.0.0.1:*)
      export DATABASE_URL=$(echo "$DATABASE_URL" | sed 's/\/\/127.0.0.1:/\/\/db:/')
      ;;
  esac
fi
if [ -n "$REDIS_URL" ]; then
  case "$REDIS_URL" in
    *@localhost:*)
      export REDIS_URL=$(echo "$REDIS_URL" | sed 's/@localhost:/@redis:/')
      ;;
    *@127.0.0.1:*)
      export REDIS_URL=$(echo "$REDIS_URL" | sed 's/@127.0.0.1:/@redis:/')
      ;;
    *//localhost:*)
      export REDIS_URL=$(echo "$REDIS_URL" | sed 's/\/\/localhost:/\/\/redis:/')
      ;;
    *//127.0.0.1:*)
      export REDIS_URL=$(echo "$REDIS_URL" | sed 's/\/\/127.0.0.1:/\/\/redis:/')
      ;;
  esac
fi

exec "$@"

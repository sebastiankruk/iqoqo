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

# Pre-start check: warn when remote object storage is configured but incomplete.
#
# Remote storage used to shell out to `rclone` and required a plaintext
# `rclone.conf` bind-mounted into this container. It now uses boto3
# (`app/core/s3_service.py`) configured entirely from environment variables, so
# there is no config file to create or permission to fix here. What remains
# worth catching at startup is a *half* configuration: a bucket named with no
# credentials, or credentials with no bucket. Either way every remote operation
# silently no-ops, and the first symptom is a missing backup archive or a cover
# cache that never populates. Failing loudly at container start is the only
# point where the operator is guaranteed to be watching.
if [ -n "$AWS_ACCESS_KEY_ID" ] || [ -n "$S3_BUCKET_BACKUP" ] || [ -n "$S3_BUCKET_COVERS" ] || [ -n "$S3_BUCKET_FEEDBACK" ]; then
  if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "WARNING: S3 storage appears configured but AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY is empty." >&2
    echo "         Remote backups and shared cover cache will be skipped. Check your .env." >&2
  fi
  if [ -z "$S3_BUCKET_BACKUP" ] && [ -z "$S3_BUCKET_COVERS" ] && [ -z "$S3_BUCKET_FEEDBACK" ]; then
    echo "WARNING: AWS credentials are present but no S3_BUCKET_* variable is set." >&2
    echo "         Remote storage is disabled; set S3_BUCKET_BACKUP to enable backup archiving." >&2
  fi
fi

# Legacy rclone.conf detection. The file is no longer read by anything, but a
# deployment that still mounts one is carrying a plaintext S3 secret into a
# container for no reason. Removing the bind-mount is the fix; this notice
# tells them exactly what to delete rather than leaving it silently unused.
if [ -e "${HOME}/.config/rclone/rclone.conf" ]; then
  echo "NOTE: ${HOME}/.config/rclone/rclone.conf is present but is no longer used." >&2
  echo "      iqoqo now uses boto3 with environment-variable credentials." >&2
  echo "      Remove the rclone.conf bind-mount from docker-compose.yml to stop" >&2
  echo "      mounting a plaintext S3 secret into the container." >&2
fi

# Auto-rewrite localhost database and redis URLs to docker service names.
#
# These run before every container start, so they avoid forking `sed` and
# `echo` per URL: parameter expansion is POSIX and allocation-free. Assigning
# and exporting separately (rather than `export VAR=$(...)`) also keeps the
# substitution's exit status from being masked by the export builtin.
if [ -n "${DATABASE_URL:-}" ]; then
  case "$DATABASE_URL" in
    *@localhost:*)   DATABASE_URL=$(printf '%s' "$DATABASE_URL" | sed 's/@localhost:/@db:/') ;;
    *@127.0.0.1:*)   DATABASE_URL=$(printf '%s' "$DATABASE_URL" | sed 's/@127.0.0.1:/@db:/') ;;
    *//localhost:*)  DATABASE_URL=$(printf '%s' "$DATABASE_URL" | sed 's|//localhost:|//db:|') ;;
    *//127.0.0.1:*)  DATABASE_URL=$(printf '%s' "$DATABASE_URL" | sed 's|//127.0.0.1:|//db:|') ;;
  esac
  export DATABASE_URL
fi
if [ -n "${REDIS_URL:-}" ]; then
  case "$REDIS_URL" in
    *@localhost:*)   REDIS_URL=$(printf '%s' "$REDIS_URL" | sed 's/@localhost:/@redis:/') ;;
    *@127.0.0.1:*)   REDIS_URL=$(printf '%s' "$REDIS_URL" | sed 's/@127.0.0.1:/@redis:/') ;;
    *//localhost:*)  REDIS_URL=$(printf '%s' "$REDIS_URL" | sed 's|//localhost:|//redis:|') ;;
    *//127.0.0.1:*)  REDIS_URL=$(printf '%s' "$REDIS_URL" | sed 's|//127.0.0.1:|//redis:|') ;;
  esac
  export REDIS_URL
fi

exec "$@"

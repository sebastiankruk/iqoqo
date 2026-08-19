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
mkdir -p "${HOME}/.config/rclone"

exec "$@"

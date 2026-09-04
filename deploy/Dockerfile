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
# Use an official Python runtime as a parent image
FROM python:3.14-slim AS builder

WORKDIR /usr/src/app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container at /usr/src/app
COPY requirements.txt ./

# Strip out testing and dev dependencies from requirements.txt to save space
RUN sed -i '/# Testing/,$d' requirements.txt && \
    pip install --user --no-cache-dir -r requirements.txt

# --- Runtime Stage ---
FROM python:3.14-slim

# Create a non-root user with UID 10001
RUN useradd -u 10001 -m -s /bin/bash appuser

# Set the working directory in the container
WORKDIR /usr/src/app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    rclone \
    && rm -rf /var/lib/apt/lists/*

# Copy site-packages from builder
COPY --chown=appuser:appuser --from=builder /root/.local /home/appuser/.local

# Add .local/bin to PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy only the necessary application code into the container
COPY --chown=appuser:appuser app app/
COPY --chown=appuser:appuser migrations migrations/
COPY --chown=appuser:appuser scripts scripts/
COPY --chown=appuser:appuser shared shared/
COPY --chown=appuser:appuser run.py wsgi.py ./

# Setup rclone config directory and copy rclone.conf if provided with 0600 permissions
RUN mkdir -p /home/appuser/.config/rclone && \
    chown -R appuser:appuser /home/appuser/.config && \
    chmod 0700 /home/appuser/.config/rclone
COPY --chown=appuser:appuser rclone.conf* /home/appuser/.config/rclone/
RUN if [ -f /home/appuser/.config/rclone/rclone.conf ]; then chmod 0600 /home/appuser/.config/rclone/rclone.conf; fi

# Copy the container entrypoint (pre-start checks, e.g. rclone config dir)
COPY deploy/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod 0755 /usr/local/bin/docker-entrypoint.sh

# Inject version
ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variable
ENV FLASK_APP=run.py

# Set HOME before switching users
ENV HOME=/home/appuser

# Switch to non-root user
USER appuser

# Run pre-start checks (rclone config dir) before any container command.
# Compose `command:` overrides replace CMD, not ENTRYPOINT, so web and
# worker services both pass through this entrypoint.
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Run the command to start the server
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info", "run:app"]

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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# Multi-stage build. Compilers live in `builder` and never reach the runtime
# image; the runtime installs pre-built wheels with no index, so it cannot
# silently compile a source distribution or reach the network at build time.
#
# OpenSpec change `devops-infrastructure-updates` §1.1-§1.3.

# ===========================================================================
# Stage 1: builder — compilers, headers, and nothing that ships
# ===========================================================================
FROM python:3.14-slim AS builder

# Compilers and Python headers are only needed to turn source distributions into
# wheels. Anything installed here would add ~300 MB to the runtime image.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

# Only the requirements file is needed to build wheels. Copying it separately
# from the application code means an application edit does not invalidate the
# (expensive) dependency build layer.
COPY requirements.txt ./

# `pip wheel` builds every dependency into /wheels and installs nothing. The
# previous approach ran `pip install --user` in this stage and then copied
# /root/.local wholesale into the runtime image, which shipped whatever
# intermediate state pip happened to leave behind.
#
# The `# Testing` section is stripped for the same reason as before: dev tools
# are not needed at runtime and pull their own transitive dependencies.
RUN sed -i '/# Testing/,$d' requirements.txt && \
    pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# ===========================================================================
# Stage 2: runtime — wheels only, no compiler, no package index
# ===========================================================================
FROM python:3.14-slim

# Only runtime shared libraries. tesseract-ocr is the OCR engine behind
# pytesseract; it is not optional, so it stays. `rclone` was removed here
# (§1.2): remote storage now goes through boto3 (app/core/s3_service.py)
# configured from environment variables, so the image needs neither the 40 MB
# CLI nor a plaintext rclone.conf bind-mounted in.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libpq5 \
    libjpeg62-turbo \
    zlib1g \
    libfreetype6 \
    && rm -rf /var/lib/apt/lists/* && \
    find /var/lib/apt/lists -mindepth 1 -delete

# Non-root user. UID is fixed because the compose bind-mounts expect it.
RUN useradd -u 10001 -m -s /bin/bash appuser

WORKDIR /usr/src/app

COPY requirements.txt ./

# Install from the wheel directory only.
#
# The wheels arrive as a BuildKit *bind mount*, not a COPY. That distinction is
# worth 125 MB: `COPY --from=builder /wheels /wheels` creates a real layer, and a
# later `rm -rf /wheels` only writes a deletion in a new layer on top of it, so
# the wheels stay in the image forever. A bind mount never enters any layer.
#
# `--no-index` is the other half of the contract: with it, pip cannot fall back
# to downloading or compiling, so this step either succeeds from the mounted
# wheels or fails loudly. Without it, a wheel that failed to build in stage 1
# would be silently compiled here -- in a stage with no compiler -- producing a
# baffling error instead of a clear one.
RUN --mount=type=bind,from=builder,source=/wheels,target=/mnt/wheels \
    sed -i '/# Testing/,$d' requirements.txt && \
    pip install --no-cache-dir --no-index --find-links=/mnt/wheels -r requirements.txt && \
    rm -f requirements.txt && \
    find /usr/local/lib/python3.14 -name '__pycache__' -type d -prune -exec rm -rf {} + && \
    find /usr/local/lib/python3.14 -name '*.pyc' -delete

# Copy only the application code the image actually serves.
COPY --chown=appuser:appuser app app/
COPY --chown=appuser:appuser migrations migrations/
COPY --chown=appuser:appuser scripts scripts/
COPY --chown=appuser:appuser shared shared/
COPY --chown=appuser:appuser docs/ontology docs/ontology/
COPY --chown=appuser:appuser run.py wsgi.py ./

# Byte-compile the application itself, after the dependency layer, so the
# bytecode is cached with the code rather than rebuilt on every code change.
RUN python -m compileall -q app migrations scripts >/dev/null 2>&1 || true

COPY deploy/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod 0755 /usr/local/bin/docker-entrypoint.sh

ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION

EXPOSE 5000

ENV FLASK_APP=run.py

# Set HOME before switching users
ENV HOME=/home/appuser

# Do not write .pyc at runtime. Byte-compilation already happened above, and
# allowing it here would let a compromised process stage a file that Python
# later executes from the writable app tree.
ENV PYTHONDONTWRITEBYTECODE=1

USER appuser

# Run pre-start checks before any container command.
# Compose `command:` overrides replace CMD, not ENTRYPOINT, so web and
# worker services both pass through this entrypoint.
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info", "run:app"]

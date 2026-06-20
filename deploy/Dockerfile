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
FROM python:3.14-slim

# Create a non-root user
RUN useradd -m -s /bin/bash appuser

# Set the working directory in the container
WORKDIR /usr/src/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container at /usr/src/app
COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Inside deploy/Dockerfile
RUN pip install opentelemetry-distro \
    opentelemetry-exporter-otlp \
    opentelemetry-instrumentation-flask \
    opentelemetry-instrumentation-celery \
    opentelemetry-instrumentation-sqlalchemy \
    opentelemetry-instrumentation-redis \
    opentelemetry-instrumentation-requests

# Run the bootstrap command to automatically install any missing instrumentation for your stack
RUN opentelemetry-bootstrap -a install

# Copy the rest of the application's code into the container
COPY . .

# Fix ownership
RUN chown -R appuser:appuser /usr/src/app

# Inject version
ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variable
ENV FLASK_APP=run.py

# Switch to non-root user
USER appuser

# Run the command to start the server
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info", "run:app"]

#!/bin/bash
# Production Deployment Script

set -e

# 1. Check for configuration
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found."
    echo "   Please copy .env.example to .env and configure your secrets."
    exit 1
fi

# Set APP_VERSION if not already set
if [ -z "$APP_VERSION" ]; then
    export APP_VERSION=$(cat VERSION)
fi

# 2. Build and Start Services
echo "🚀 Starting iqoqo production deployment (Version: $APP_VERSION)..."
docker compose -f docker-compose.prod.yml up -d --build --remove-orphans

echo "✅ Deployment successful!"
echo "🌍 Nginx is listening on port ${NGINX_PORT:-8000}"

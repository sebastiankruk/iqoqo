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
.PHONY: help start stop lint lint-python lint-format lint-js lint-ts lint-css lint-markdown lint-frontend format format-python format-js test test-backend test-frontend test-e2e test-e2e-db-up _test-e2e-run clean db-init db-seed db-reset db-export docker-backup db-stats init-auth build-frontend generate-taxonomy pg-create-schemas mobile-build mobile-sync mobile-ios mobile-android mobile-run-ios mobile-run-android

# Detect node/npm/npx - works even when make is invoked from a non-interactive
# shell that hasn't sourced nvm (e.g. IDE terminals, CI). We find the node
# binary's directory and prepend it to PATH so that '#!/usr/bin/env node'
# shebangs in npm/npx scripts resolve correctly.
NODE     := $(shell command -v node 2>/dev/null || ls $(HOME)/.nvm/versions/node/*/bin/node 2>/dev/null | sort -V | tail -1)
NODE_DIR := $(dir $(NODE))

# Safely define NPM/NPX only if node was found, otherwise fallback to system default
ifeq ($(NODE),)
NPM = npm
NPX = npx
else
NPM = PATH="$(NODE_DIR):$$PATH" $(NODE_DIR)npm
NPX = PATH="$(NODE_DIR):$$PATH" $(NODE_DIR)npx
endif

# Docker compose configuration for production/preview targets
COMPOSE_FILE     ?= docker-compose.prod.yml
COMPOSE_PROJECT  ?= iqoqo
COMPOSE_ENV_FILE ?= .env

help:
	@echo "Available targets:"
	@echo ""
	@echo "Development:"
	@echo "  start          - Start development environment (DB, Flask API, Next.js frontend)"
	@echo "  stop           - Stop all development servers and containers"
	@echo ""
	@echo "Code quality:"
	@echo "  lint           - Run all linting checks"
	@echo "  lint-python    - Run Python linters (ruff, mypy, pylint)"
	@echo "  lint-format    - Check Python code formatting (black)"
	@echo "  lint-js        - Run legacy JavaScript linter (eslint)"
	@echo "  lint-frontend  - Run Next.js / TypeScript linter"
	@echo "  lint-css       - Run CSS linter (stylelint)"
	@echo "  lint-markdown  - Run Markdown linter"
	@echo "  lint-license   - Check copyright headers"
	@echo "  format         - Format all code"
	@echo "  format-python  - Format Python code (black, isort)"
	@echo "  format-js      - Format JavaScript code (prettier)"
	@echo "  test           - Run all tests (backend and frontend)"
	@echo "  test-backend   - Run backend tests (pytest)"
	@echo "  test-frontend  - Run frontend unit tests (Vitest)"
	@echo "  test-e2e       - Run end-to-end tests (Playwright). Loads .env.test automatically."
	@echo "  build-frontend - Build Next.js production bundle"
	@echo "  clean          - Remove build artifacts"
	@echo ""
	@echo "Database targets:"
	@echo "  db-init       - Initialize database with seed data"
	@echo "  db-seed       - Load seed data into existing database"
	@echo "  db-export     - Export database to data/backup.json"
	@echo "  docker-backup - Create full ZIP backup in ./exports (via Docker)"
	@echo "  db-stats      - Show database statistics"
	@echo ""
	@echo "Version updates:"
	@echo "  bump-version  - Bump version (v=major|minor|patch) and sync files"
	@echo "  sync-version  - Sync version from pyproject.toml to package.json files"
	@echo "  generate-taxonomy - Generate taxonomy constants from shared/taxonomy.yaml"

# Versioning targets
sync-version:
	@echo "Syncing version from pyproject.toml to package.json files..."
	@.venv/bin/python scripts/sync_version.py

generate-taxonomy:
	@echo "Generating taxonomies from YAML..."
	@.venv/bin/python scripts/generate_taxonomy.py

bump-version:
	@if [ -z "$(v)" ]; then \
		echo "Usage: make bump-version v=[major|minor|patch]"; \
		exit 1; \
	fi
	@echo "Bumping version ($(v))..."
	@.venv/bin/python scripts/sync_version.py --bump $(v)

# Development targets
init:
	@echo "Initializing development environment..."
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	cd frontend && npm install

start:
	@echo "Starting development environment..."
	@./run.sh dev

stop:
	@echo "Stopping Flask server..."
	@if [ -f .pids/flask.pid ]; then \
		FLASK_PID=$$(cat .pids/flask.pid); \
		if kill -0 $$FLASK_PID 2>/dev/null; then \
			kill $$FLASK_PID; \
			echo "Sent SIGTERM to Flask (PID $$FLASK_PID)."; \
		else \
			echo "Flask PID $$FLASK_PID is not running."; \
		fi; \
		rm -f .pids/flask.pid; \
	fi
	@echo "Stopping Celery worker..."
	@if [ -f .pids/celery.pid ]; then \
		CELERY_PID=$$(cat .pids/celery.pid); \
		if kill -0 $$CELERY_PID 2>/dev/null; then \
			kill $$CELERY_PID; \
			echo "Sent SIGTERM to Celery (PID $$CELERY_PID)."; \
		else \
			echo "Celery PID $$CELERY_PID is not running."; \
		fi; \
		rm -f .pids/celery.pid; \
	fi
	@echo "Stopping Next.js frontend..."
	@if [ -f .pids/next.pid ]; then \
		NEXT_PID=$$(cat .pids/next.pid); \
		if kill -0 $$NEXT_PID 2>/dev/null; then \
			kill $$NEXT_PID; \
			echo "Sent SIGTERM to Next.js (PID $$NEXT_PID)."; \
		else \
			echo "Frontend PID $$NEXT_PID is not running."; \
		fi; \
		rm -f .pids/next.pid; \
	fi
	@echo "Stopping database containers..."
	@docker compose stop
	@rm -rf .pids
	@echo "Development environment stopped."

# Linting targets
lint-python:
	@echo "Running ruff..."
	.venv/bin/ruff check app/ tests/ scripts/
	@echo "Running mypy..."
	rm -rf .mypy_cache || true
	.venv/bin/mypy app/ tests/
	@echo "Running pylint..."
	.venv/bin/pylint app/ tests/ scripts/

lint-format:
	@echo "Checking Python formatting..."
	.venv/bin/black --check app/ tests/ scripts/
	.venv/bin/isort --check-only app/ tests/ scripts/

lint-js:
	@echo "Running eslint..."
	@cd frontend && $(NPM) run lint

lint-ts:
	@echo "Running TypeScript type checks..."
	@cd frontend && $(NPX) tsc --noEmit

lint-frontend: lint-js lint-ts

build-frontend:
	@echo "Building Next.js production bundle..."
	@cd frontend && npm run build

lint-license:
	@echo "Checking copyright headers..."
	./scripts/check_license.sh

lint-css:
	@echo "Running stylelint..."
	$(NPX) stylelint --allow-empty-input "frontend/app/**/*.css" "frontend/components/**/*.css"

lint-markdown:
	@echo "Running markdownlint..."
	$(NPX) markdownlint-cli2 "**/*.md" "#node_modules" "#.venv" "#frontend/node_modules" "#frontend/.next" "#.github" "#.pytest_cache" "#.agents" "#frontend/playwright-report" "#frontend/test-results" "#context"

# Run all linting checks (stops on first failure)
lint: lint-python lint-format lint-js lint-ts lint-css lint-markdown lint-license
	@echo "All linting checks passed!"

# Formatting targets
format-python:
	@echo "Formatting Python code..."
	.venv/bin/black app/ tests/ scripts/
	.venv/bin/isort app/ tests/ scripts/

format-js:
	@echo "Formatting frontend TypeScript and CSS..."
	@cd frontend && $(NPX) prettier --write "**/*.{ts,tsx,css}" --ignore-path .gitignore

format: format-python format-js
	@echo "All code formatted!"

# Testing
test-backend:
	@echo "Running backend tests..."
	.venv/bin/pytest tests/

test-frontend:
	@echo "Running frontend unit tests (Vitest)..."
	cd frontend && $(NPM) run test

# Helper: ensure PostgreSQL schemas exist before db.create_all() runs.
# Safe to call on SQLite (psql not installed; the app creates public only).
pg-create-schemas:
	@if command -v psql > /dev/null 2>&1 && echo "$$DATABASE_URL" | grep -q 'postgresql'; then \
		echo "Creating PostgreSQL schemas (auth, catalog, inventory) if missing..."; \
		psql "$$DATABASE_URL" -c "CREATE SCHEMA IF NOT EXISTS auth;" 2>&1 | grep -v 'already exists' || true; \
		psql "$$DATABASE_URL" -c "CREATE SCHEMA IF NOT EXISTS catalog;" 2>&1 | grep -v 'already exists' || true; \
		psql "$$DATABASE_URL" -c "CREATE SCHEMA IF NOT EXISTS inventory;" 2>&1 | grep -v 'already exists' || true; \
	fi

# Start the Docker DB (and Redis) for E2E tests, then wait until pg_isready.
# Also creates the dedicated test database (iqoqo_test) if it doesn't exist.
test-e2e-db-up:
	@echo "Ensuring Docker DB and Redis are running for E2E tests..."
	@docker compose up -d db redis
	@echo "Waiting for PostgreSQL to be ready..."
	@for i in $$(seq 1 30); do \
		if docker compose exec -T db pg_isready -U "$${POSTGRES_USER:-iqoqo}" -d "$${POSTGRES_DB:-iqoqo}" > /dev/null 2>&1; then \
			echo "PostgreSQL is ready."; \
			break; \
		fi; \
		if [ "$$i" = "30" ]; then echo "ERROR: PostgreSQL did not become ready in time."; exit 1; fi; \
		echo "Waiting... ($$i/30)"; \
		sleep 1; \
	done
	@echo "Ensuring test database exists..."
	@docker compose exec -T db psql -U "$${POSTGRES_USER:-iqoqo}" -d postgres \
		-tc "SELECT 1 FROM pg_database WHERE datname='iqoqo_test'" \
		| grep -q 1 \
		|| docker compose exec -T db createdb -U "$${POSTGRES_USER:-iqoqo}" iqoqo_test \
		&& echo "Test database iqoqo_test ready." || true

test-e2e: test-e2e-db-up
	@# Load .env.test to provide DATABASE_URL_TEST (and other test settings) when
	@# they are not already present in the shell environment. This file is safe to
	@# commit because it contains only non-secret test credentials.
	@if [ -z "$$DATABASE_URL_TEST" ] && [ -f .env.test ]; then \
		echo "Loading test environment from .env.test..."; \
		export $$(grep -v '^#' .env.test | grep -v '^$$' | xargs); \
		$(MAKE) _test-e2e-run DATABASE_URL_TEST="$$DATABASE_URL_TEST" NO_RESET="$(NO_RESET)"; \
	else \
		$(MAKE) _test-e2e-run DATABASE_URL_TEST="$$DATABASE_URL_TEST" NO_RESET="$(NO_RESET)"; \
	fi

# Internal target — called by test-e2e after env vars are resolved.
_test-e2e-run:
	@if [ -z "$(NO_RESET)" ]; then \
		if [ -z "$(DATABASE_URL_TEST)" ]; then \
			echo "ERROR: DATABASE_URL_TEST is not set."; \
			echo "  E2E tests reset the database and MUST use a dedicated test DB."; \
			echo "  Either:"; \
			echo "    1. Create .env.test with DATABASE_URL_TEST=postgresql://... (recommended)"; \
			echo "    2. Set DATABASE_URL_TEST in your shell before running make test-e2e"; \
			echo "    3. Use NO_RESET=1 to skip the DB reset (dangerous — stale data!)"; \
			exit 1; \
		fi; \
		echo "Resetting test database for E2E tests (DATABASE_URL_TEST=$(DATABASE_URL_TEST))..."; \
		DATABASE_URL="$(DATABASE_URL_TEST)" $(MAKE) pg-create-schemas; \
		DATABASE_URL="$(DATABASE_URL_TEST)" $(MAKE) db-reset; \
		DATABASE_URL="$(DATABASE_URL_TEST)" ADMIN_PASSWORD="$${ADMIN_PASSWORD:-admin}" $(MAKE) init-auth; \
		DATABASE_URL="$(DATABASE_URL_TEST)" $(MAKE) db-seed-e2e; \
		echo "Killing old Flask server on port 5000 (if any) to ensure clean start against test DB..."; \
		lsof -ti tcp:5000 | xargs kill -9 2>/dev/null || true; \
	else \
		echo "Skipping database reset (NO_RESET is set)..."; \
	fi
	@echo "Running end-to-end tests (Playwright)..."
	cd frontend && DATABASE_URL_TEST="$(DATABASE_URL_TEST)" $(NPX) playwright test


test: test-backend test-frontend test-e2e
	@echo "All tests completed!"

# Clean
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +

# Database targets
# Note: pg-create-schemas is defined above (near test-e2e) so it can be
# referenced by both test-e2e and db-reset.
db-init:
	@echo "Initializing database with seed data..."
	.venv/bin/python scripts/init_db.py --seed-file data/seed_example.json

db-seed:
	@echo "Loading seed data..."
	.venv/bin/python scripts/init_db.py --seed-file data/seed_example.json

db-seed-e2e:
	@echo "Loading E2E specific seed data..."
	PYTHONPATH=. .venv/bin/python tests/e2e/scripts/seed_e2e.py

db-export:
	@echo "Exporting database to data/backup.json..."
	@.venv/bin/python -c "from app import create_app; from app.core.data_manager import DataManager; \
		app = create_app(); \
		with app.app_context(): DataManager.export_to_file('data/backup.json')"
	@echo "Export complete: data/backup.json"

docker-backup:
	@echo "Creating full backup in Docker (Project: $(COMPOSE_PROJECT), Env: $(COMPOSE_ENV_FILE))..."
	@ENV_FILE=$(COMPOSE_ENV_FILE) docker compose -p $(COMPOSE_PROJECT) -f $(COMPOSE_FILE) --env-file $(COMPOSE_ENV_FILE) exec -T web env PYTHONPATH=. python scripts/backup.py
	@echo "Backup complete! Check the ./exports folder on your host."

db-reset: pg-create-schemas
	@echo "Resetting database..."
	.venv/bin/python scripts/init_db.py --seed-file data/seed_example.json --reset

init-auth:
	@echo "Initializing auth (roles, permissions, admin user)..."
	ADMIN_PASSWORD=admin PYTHONPATH=. .venv/bin/python scripts/init_auth.py

db-stats:
	@echo "Database statistics:"
	@.venv/bin/python -c "from app import create_app; from app.core.data_manager import DataManager; \
		app = create_app(); \
		with app.app_context(): \
			stats = DataManager.get_stats(); \
			print(f\"  Works: {stats['works']}\"); \
			print(f\"  Expressions: {stats['expressions']}\"); \
			print(f\"  Manifestations: {stats['manifestations']}\"); \
			print(f\"  Items: {stats['items']}\"); \
			print(f\"  Total: {sum(stats.values())}\")"

sync-permissions:
	@echo "Synchronizing permissions (Code & Database)..."
	@PYTHONPATH=. .venv/bin/python scripts/sync_permissions.py
	@PYTHONPATH=. .venv/bin/python scripts/init_auth.py
	@echo "Permissions synchronized successfully."

verify-perms:
	@echo "Verifying permissions are synchronized"
	.venv/bin/python scripts/sync_permissions.py --verify

## ─── Mobile / Capacitor Targets ────────────────────────────────────────────

mobile-build: ## Build frontend static export for Capacitor (sets CAPACITOR_BUILD=true)
	@# Swap in the static stub for the auth-exchange route (output:export forbids
	@# dynamic route handlers; the native app never calls this endpoint anyway).
	@# `git restore` is used to reset route.ts cleanly on success or failure.
	@cd frontend && \
	  cp app/api/auth-exchange/route.capacitor.ts app/api/auth-exchange/route.ts && \
	  CAPACITOR_BUILD=true npm run build; \
	  BUILD_EXIT=$$?; \
	  git restore app/api/auth-exchange/route.ts; \
	  exit $$BUILD_EXIT

mobile-sync: mobile-build ## Sync static web assets into both native projects
	cd frontend && npx cap sync

mobile-ios: mobile-sync ## Open the iOS project in Xcode
	cd frontend && npx cap open ios

mobile-android: mobile-sync ## Open the Android project in Android Studio
	cd frontend && npx cap open android

mobile-run-ios: mobile-sync ## Deploy & run on a connected iOS device (sideload)
	cd frontend && npx cap run ios

mobile-run-android: mobile-sync ## Deploy & run on a connected Android device (sideload / ADB)
	cd frontend && npx cap run android

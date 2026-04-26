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
.PHONY: help start stop lint lint-python lint-format lint-js lint-ts lint-css lint-markdown lint-frontend format format-python format-js test test-backend test-frontend test-e2e clean db-init db-seed db-export docker-backup db-stats build-frontend

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
	@echo "  format         - Format all code"
	@echo "  format-python  - Format Python code (black, isort)"
	@echo "  format-js      - Format JavaScript code (prettier)"
	@echo "  test           - Run all tests (backend and frontend)"
	@echo "  test-backend   - Run backend tests (pytest)"
	@echo "  test-frontend  - Run frontend unit tests (Vitest)"
	@echo "  test-e2e       - Run end-to-end tests (Playwright, requires running app)"
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

# Versioning targets
sync-version:
	@echo "Syncing version from pyproject.toml to package.json files..."
	@.venv/bin/python scripts/sync_version.py

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
	@./run_dev.sh

stop:
	@echo "Stopping Flask server..."
	@if [ -f .flask.pid ]; then \
		FLASK_PID=$$(cat .flask.pid); \
		if kill -0 $$FLASK_PID 2>/dev/null; then \
			kill $$FLASK_PID; \
			echo "Sent SIGTERM to Flask (PID $$FLASK_PID)."; \
		else \
			echo "Flask PID $$FLASK_PID is not running."; \
		fi; \
		rm -f .flask.pid; \
	else \
		echo "No Flask PID file found (.flask.pid); skipping Flask stop."; \
	fi
	@echo "Stopping Next.js frontend..."
	@if [ -f .frontend.pid ]; then \
		FRONTEND_PID=$$(cat .frontend.pid); \
		if kill -0 $$FRONTEND_PID 2>/dev/null; then \
			kill $$FRONTEND_PID; \
			echo "Sent SIGTERM to Next.js (PID $$FRONTEND_PID)."; \
		else \
			echo "Frontend PID $$FRONTEND_PID is not running."; \
		fi; \
		rm -f .frontend.pid; \
	else \
		echo "No frontend PID file found (.frontend.pid); skipping frontend stop."; \
	fi
	@echo "Stopping database containers..."
	@docker compose stop
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
	$(NPX) markdownlint-cli2 "**/*.md" "#node_modules" "#.venv" "#frontend/node_modules" "#frontend/.next" "#.github" "#.pytest_cache" "#.agents" "#frontend/playwright-report" "#frontend/test-results"

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

test-e2e:
	@echo "Running end-to-end tests (Playwright)..."
	cd frontend && $(NPX) playwright test

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
db-init:
	@echo "Initializing database with seed data..."
	.venv/bin/python scripts/init_db.py --seed-file data/seed_example.json

db-seed:
	@echo "Loading seed data..."
	.venv/bin/python scripts/init_db.py --seed-file data/seed_example.json

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

sync-perms:
	@echo "Syncing permissions from shared/permissions.yaml"
	.venv/bin/python scripts/sync_permissions.py

verify-perms:
	@echo "Verifying permissions are synchronized"
	.venv/bin/python scripts/sync_permissions.py --verify

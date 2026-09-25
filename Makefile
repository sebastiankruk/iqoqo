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
.PHONY: help status start stop monitoring-start monitoring-stop lint lint-all lint-python lint-format lint-js lint-ts lint-css lint-markdown lint-frontend format format-python format-js test test-backend test-backend-pg test-frontend test-scripts-bash test-scripts-python test-e2e test-e2e-db-up _test-e2e-run clean db-init db-seed db-reset db-export backup-run backup-install backup-uninstall backup-check db-stats init-auth build-frontend generate-taxonomy pg-create-schemas retry-missing-covers fetch-covers refetch-metadata db-stamp db-upgrade dev allegro-auth fix-physical-kinds mempalace-index mempalace-scope mempalace-status codegraph-sync codegraph-index codegraph-status mykg-scope mykg-update mykg-index mykg-status mykg-ask graphify-update graphify-index graphify-status memory-presync knowledge-sync knowledge-sync-full version audit-frbr etl-frbr sync-ontology

SHELL := /bin/bash

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

# Dynamic mode detection from target goals (e.g. make start preview prebuilt)
MODE ?= dev
ifeq ($(filter preview,$(MAKECMDGOALS)),preview)
  MODE = preview
endif
ifeq ($(filter prod,$(MAKECMDGOALS)),prod)
  MODE = prod
endif

# Docker compose configuration for production/preview targets
COMPOSE_FILE     ?= docker-compose.prebuilt.yml
COMPOSE_PROJECT  ?= iqoqo
COMPOSE_ENV_FILE ?= .env

ifeq ($(MODE),preview)
  COMPOSE_ENV_FILE = .env.preview
  COMPOSE_PROJECT  = iqoqo-preview
  USE_DOCKER ?= true
endif
ifeq ($(MODE),prod)
  COMPOSE_PROJECT  = iqoqo
  ifneq ($(wildcard .env.prod),)
    COMPOSE_ENV_FILE = .env.prod
  else
    COMPOSE_ENV_FILE = .env
  endif
  USE_DOCKER ?= true
endif

# When adding a Make target that writes files inside a Docker container, ensure
# the output directory is mounted as a volume in docker-compose.yml under `web`
# (and `worker` if applicable). Otherwise the files vanish on container restart.
# Currently mounted:  ./exports  ./app/static/covers  ./app/static/gallery
# If your target writes elsewhere, add the mount first.

# Python execution context: set USE_DOCKER=true to run against a running container
ifeq ($(USE_DOCKER),true)
PYTHON_CMD = ENV_FILE=$(COMPOSE_ENV_FILE) docker compose -p $(COMPOSE_PROJECT) -f $(COMPOSE_FILE) --env-file $(COMPOSE_ENV_FILE) exec -T web env PYTHONPATH=. python
else
PYTHON_CMD = ADMIN_PASSWORD=admin PYTHONPATH=. .venv/bin/python
endif

# AiOps / Terse mode flags and banner suppression
ifeq ($(IQOQO_AI_MODE),1)
RUFF_FLAGS    ?= --output-format=concise
PYLINT_FLAGS  ?= --msg-template='{path}:{line}: {msg} ({symbol})'
MYPY_FLAGS    ?= --no-error-summary
AI_ECHO       := @:
else
RUFF_FLAGS    ?=
PYLINT_FLAGS  ?=
MYPY_FLAGS    ?=
AI_ECHO       := @echo
endif

# Auto-detect project version from package.json or pyproject.toml without requiring host python
IQOQO_VERSION ?= $(shell (grep -m 1 '"version":' package.json 2>/dev/null | cut -d '"' -f 4) || (grep -m 1 'version = ' pyproject.toml 2>/dev/null | cut -d '"' -f 2) || echo "unknown")
PREBUILT_TAG ?= $(if $(APP_VERSION),$(APP_VERSION),$(if $(filter-out unknown,$(IQOQO_VERSION)),$(IQOQO_VERSION),latest))
IMAGE_PREFIX ?= ghcr.io/sebastiankruk/

help:
	@echo "Available targets:"
	@echo ""
	@echo "Building:"
	@echo "  build-frontend - Build Next.js production bundle"
	@echo "  clean          - Remove build artifacts"
	@echo ""
	@echo "Code quality:"
	@echo "  lint           - Run checks that actually gate GitHub quality CI"
	@echo "  lint-all       - Run canonical lint plus stricter local-only checks"
	@echo "  lint-python    - Run Python linters (ruff, mypy, pylint)"
	@echo "  lint-format    - Check Python code formatting (black)"
	@echo "  lint-js        - Run legacy JavaScript linter (eslint)"
	@echo "  lint-frontend  - Run Next.js / TypeScript linter"
	@echo "  lint-css       - Run CSS linter (stylelint)"
	@echo "  lint-markdown  - Run Markdown linter"
	@echo "  lint-license   - Check copyright headers"
	@echo "  validate-yaml  - Validate YAML configuration files"
	@echo "  format         - Format all code"
	@echo "  format-python  - Format Python code (black, isort)"
	@echo "  format-js      - Format JavaScript code (prettier)"
	@echo "  test           - Run all tests (backend and frontend)"
	@echo "  test-backend   - Run backend tests (pytest, defaults to SQLite)"
	@echo "  test-backend-pg - Run backend integration tests requiring PostgreSQL"
	@echo "  test-frontend  - Run frontend unit tests (Vitest)"
	@echo "  test-e2e       - Run Playwright against an isolated E2E-only PostgreSQL service."
	@echo ""
	@echo "Deployment:"
	@echo "  start          - Start development environment (DB, Flask API, Next.js frontend)"
	@echo "  stop           - Stop all development servers and containers"
	@echo "  docker-build   - Build backend, frontend, and nginx Docker images locally (TAG=...)"
	@echo "  docker-build-preview - Build all images locally tagged for preview environment"
	@echo ""
	@echo "Database targets:"
	@echo "  db-init       - Initialize database with seed data"
	@echo "  db-seed       - Load seed data into existing database"
	@echo "  db-export     - Export database to exports/backup.json (USE_DOCKER=true for Docker)"
	@echo "  db-stats      - Show database statistics (USE_DOCKER=true for Docker)"
	@echo "  db-stamp      - Stamp database migration version to head (USE_DOCKER=true for Docker)"
	@echo "  db-upgrade    - Upgrade database schema to head (USE_DOCKER=true for Docker)"
	@echo ""
	@echo "Backup targets:"
	@echo "  backup-run       - Run cloud backup immediately (remote=<name>)"
	@echo "  backup-install   - Install daily 03:00 backup cron (remote=<name>)"
	@echo "  backup-uninstall - Remove installed backup cron job"
	@echo "  backup-check     - Verify backup health (cron, rclone, disk, freshness)"
	@echo ""
	@echo "Curation:"
	@echo "  retry-missing-covers - Retry processing covers for manifestations missing covers (supports preview|prod)"
	@echo "  fetch-covers  - Fetch covers for all manifestations missing covers (supports preview|prod, force=true)"
	@echo "  refetch-metadata - Refetch missing metadata from external APIs (supports gap=all|format|publisher|genres|cover, content-type=text|music|movie|board_game|puzzle, limit=N, force=true, dry-run=true)"
	@echo "  fix-physical-kinds - Audit and fix non-canonical format values (supports ARGS=\"--interactive\" and ARGS=\"--apply --dry-run\")"
	@echo ""
	@echo "Monitoring:"
	@echo "  - OpenObserve + OTel Collector start automatically with the main stack (make start)"
	@echo "  status          - Show health status of all services (--stack preview|prod)"
	@echo ""
	@echo "Version management:"
	@echo "  bump-version  - Bump version (v=major|minor|patch) and sync files"
	@echo "  sync-version  - Sync version from pyproject.toml to package.json files"
	@echo ""
	@echo "Semantic Web:"
	@echo "  generate-taxonomy - Generate taxonomy constants from shared/taxonomy.yaml"
	@echo "  audit-frbr        - Run FRBR database integrity audit (USE_DOCKER=true for production, supports ARGS=\"--json --verbose\")"
	@echo "  etl-frbr          - Run FRBR ETL strict cleanup (USE_DOCKER=true for production, supports ARGS=\"--dry-run --verbose\")"
	@echo "  sync-ontology     - Check ontology sync with DB models (USE_DOCKER=true for production)"
	@echo ""
	@echo "Knowledge Sync:"
	@echo "  knowledge-sync      - Fast memory sync: session + graphify/codegraph (parallel, <45s)"
	@echo "  knowledge-sync-full - Full memory sync: fast sync + mempalace-index + mykg-update"
	@echo "  memory-presync      - Sync agy session transcripts to .context/ai-memory/ (jsonl->md)"
	@echo "  mykg-ask            - Query latest myKG knowledge graph: make mykg-ask Q=\"...\""

# Versioning targets
sync-version: .venv/bin/activate
	@echo "Syncing version from pyproject.toml to package.json files..."
	@.venv/bin/python scripts/sync_version.py

generate-taxonomy: .venv/bin/activate
	@echo "Generating taxonomies from YAML..."
	@.venv/bin/python scripts/generate_taxonomy.py

# Knowledge graph & MemPalace targets
mempalace-scope: .venv/bin/activate
	@.venv/bin/python .agents/skills/iqoqo-mempalace/scripts/scan_scope.py

mempalace-index: .venv/bin/activate
	$(AI_ECHO) "Mining scoped codebase and notes into MemPalace..."
	@.venv/bin/python .agents/skills/iqoqo-mempalace/scripts/run_mine.py $(if $(ARGS),$(ARGS),)

mempalace-status: .venv/bin/activate
	@.venv/bin/python .agents/skills/iqoqo-mempalace/scripts/get_status.py

# CodeGraph targets
codegraph-sync:
	@codegraph sync

codegraph-index:
	@codegraph index

codegraph-status:
	@codegraph status

# myKG targets
MYKG_DEFAULT_MODEL ?= gemini-3.8-flash-low
MYKG_DEFAULT_EFFORT ?= low
AI_AGENT ?= agy
AGY_DEFAULT_MODEL ?= gemini-3.8-flash-low
AGY_DEFAULT_EFFORT ?= low
OPENCODE_DEFAULT_MODEL ?= opencode/mimo-v2.5-free
OPENCODE_DEFAULT_EFFORT ?= minimal
AI_EFFECTIVE_MODEL = $(if $(MODEL),$(MODEL),$(if $(filter agy,$(AI_AGENT)),$(AGY_DEFAULT_MODEL),$(OPENCODE_DEFAULT_MODEL)))
AI_EFFECTIVE_EFFORT = $(if $(EFFORT),$(EFFORT),$(if $(filter agy,$(AI_AGENT)),$(AGY_DEFAULT_EFFORT),$(OPENCODE_DEFAULT_EFFORT)))
AI_PROFILE = $(if $(filter opencode,$(AI_AGENT)),agent-opencode,agent-claude-code)
ifeq ($(filter agy opencode,$(AI_AGENT)),)
$(error Invalid AI_AGENT '$(AI_AGENT)'. Valid options: agy, opencode)
endif

mykg-scope: .venv/bin/activate
	@.venv/bin/python .agents/skills/iqoqo-mykg/scripts/scan_scope.py

mykg-update: .venv/bin/activate
	$(AI_ECHO) "Running autonomous mykg update with Docker sandbox (AI_AGENT=$(AI_AGENT), MODEL=$(AI_EFFECTIVE_MODEL), EFFORT=$(AI_EFFECTIVE_EFFORT))..."
	@.venv/bin/python .agents/skills/iqoqo-mykg/scripts/scan_scope.py --check
	@cleanup() { \
		EXIT_CODE=$$?; \
		trap - EXIT INT TERM; \
		if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then \
			docker compose -f docker-compose.ai_sandbox.yml down >/dev/null 2>&1 || true; \
			docker rm -f mykg-agy-daemon >/dev/null 2>&1 || true; \
			docker rm -f mykg-opencode-daemon >/dev/null 2>&1 || true; \
		fi; \
		exit $$EXIT_CODE; \
	}; \
	trap cleanup EXIT INT TERM; \
	SESS_DIR=$$(.venv/bin/python -c "import pathlib, sys; p = pathlib.Path('mykg_sessions'); \
		target = p.resolve() if p.exists() else pathlib.Path('.mykg_sessions').resolve(); \
		sessions = sorted([d for d in target.iterdir() if d.is_dir()], key=lambda x: x.stat().st_mtime, reverse=True) if target.exists() else []; \
		print(str(sessions[0])) if sessions else sys.exit(0)"); \
	if [ -n "$$SESS_DIR" ] && command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then \
		mkdir -p "$$SESS_DIR/intermediate/agent_inbox" "$$SESS_DIR/intermediate/agent_outbox"; \
		if [ "$(AI_AGENT)" = "opencode" ]; then \
			AI_BIN=$$(which opencode 2>/dev/null || echo ""); \
			AI_CONTAINER="mykg-opencode-daemon"; \
			AI_MOUNT="/usr/local/bin/opencode:ro"; \
			AI_SCRIPT=".agents/skills/iqoqo-mykg/scripts/opencode_daemon.py"; \
		else \
			AI_BIN=$$(which agy 2>/dev/null || echo ""); \
			AI_CONTAINER="mykg-agy-daemon"; \
			AI_MOUNT="/usr/local/bin/agy:ro"; \
			AI_SCRIPT=".agents/skills/iqoqo-mykg/scripts/agy_daemon.py"; \
		fi; \
	if [ -n "$$AI_BIN" ]; then \
		docker rm -f "$$AI_CONTAINER" >/dev/null 2>&1 || true; \
		docker compose -f docker-compose.ai_sandbox.yml stop sandbox-egress-proxy >/dev/null 2>&1 || true; \
		docker compose -f docker-compose.ai_sandbox.yml rm -f sandbox-egress-proxy >/dev/null 2>&1 || true; \
		AI_AGENT="$(AI_AGENT)" docker compose -f docker-compose.ai_sandbox.yml up -d sandbox-egress-proxy >/dev/null 2>&1 || true; \
		AI_AGENT="$(AI_AGENT)" docker compose -f docker-compose.ai_sandbox.yml run --rm -d --name "$$AI_CONTAINER" \
			-v "$$AI_BIN:$$AI_MOUNT" \
			-e MYKG_MODEL="$(AI_EFFECTIVE_MODEL)" \
			-e MYKG_EFFORT="$(AI_EFFECTIVE_EFFORT)" \
			-e OPENCODE_MODEL="$(AI_EFFECTIVE_MODEL)" \
			-e OPENCODE_EFFORT="$(AI_EFFECTIVE_EFFORT)" \
			-e AI_AGENT="$(AI_AGENT)" \
			"$$AI_CONTAINER" \
			python3 "$$AI_SCRIPT" \
			--workers 1 \
			"mykg_sessions/$$(basename $$SESS_DIR)/intermediate/agent_inbox" \
			"mykg_sessions/$$(basename $$SESS_DIR)/intermediate/agent_outbox" >/dev/null 2>&1 || true; \
	fi; \
	fi; \
	MYKG_PROFILE="$(AI_PROFILE)" .venv/bin/python .agents/skills/iqoqo-mykg/scripts/run_update.py $(if $(ARGS),$(ARGS),); \
	EXIT_CODE=$$?; \
	exit $$EXIT_CODE

mykg-index: .venv/bin/activate
	$(AI_ECHO) "Running full mykg index with Docker sandbox (AI_AGENT=$(AI_AGENT), MODEL=$(AI_EFFECTIVE_MODEL), EFFORT=$(AI_EFFECTIVE_EFFORT))..."
	@.venv/bin/python .agents/skills/iqoqo-mykg/scripts/scan_scope.py
	@cleanup() { \
		EXIT_CODE=$$?; \
		trap - EXIT INT TERM; \
		if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then \
			docker compose -f docker-compose.ai_sandbox.yml down >/dev/null 2>&1 || true; \
			docker rm -f mykg-agy-daemon >/dev/null 2>&1 || true; \
			docker rm -f mykg-opencode-daemon >/dev/null 2>&1 || true; \
		fi; \
		exit $$EXIT_CODE; \
	}; \
	trap cleanup EXIT INT TERM; \
	if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then \
		mkdir -p "mykg_sessions"; \
		if [ "$(AI_AGENT)" = "opencode" ]; then \
			AI_BIN=$$(which opencode 2>/dev/null || echo ""); \
			AI_CONTAINER="mykg-opencode-daemon"; \
			AI_MOUNT="/usr/local/bin/opencode:ro"; \
			AI_SCRIPT=".agents/skills/iqoqo-mykg/scripts/opencode_daemon.py"; \
		else \
			AI_BIN=$$(which agy 2>/dev/null || echo ""); \
			AI_CONTAINER="mykg-agy-daemon"; \
			AI_MOUNT="/usr/local/bin/agy:ro"; \
			AI_SCRIPT=".agents/skills/iqoqo-mykg/scripts/agy_daemon.py"; \
		fi; \
		if [ -n "$$AI_BIN" ]; then \
			docker rm -f "$$AI_CONTAINER" >/dev/null 2>&1 || true; \
			docker compose -f docker-compose.ai_sandbox.yml stop sandbox-egress-proxy >/dev/null 2>&1 || true; \
			docker compose -f docker-compose.ai_sandbox.yml rm -f sandbox-egress-proxy >/dev/null 2>&1 || true; \
			AI_AGENT="$(AI_AGENT)" docker compose -f docker-compose.ai_sandbox.yml up -d sandbox-egress-proxy >/dev/null 2>&1 || true; \
			AI_AGENT="$(AI_AGENT)" docker compose -f docker-compose.ai_sandbox.yml run --rm -d --name "$$AI_CONTAINER" \
				-v "$$AI_BIN:$$AI_MOUNT" \
				-e MYKG_MODEL="$(AI_EFFECTIVE_MODEL)" \
				-e MYKG_EFFORT="$(AI_EFFECTIVE_EFFORT)" \
				-e OPENCODE_MODEL="$(AI_EFFECTIVE_MODEL)" \
				-e OPENCODE_EFFORT="$(AI_EFFECTIVE_EFFORT)" \
				-e AI_AGENT="$(AI_AGENT)" \
				"$$AI_CONTAINER" \
				python3 "$$AI_SCRIPT" \
				--workers 1 \
				"mykg_sessions" \
				"mykg_sessions" >/dev/null 2>&1 || true; \
		fi; \
	fi; \
	MYKG_PROFILE="$(AI_PROFILE)" .venv/bin/python .agents/skills/iqoqo-mykg/scripts/run_index.py $(if $(ARGS),$(ARGS),); \
	EXIT_CODE=$$?; \
	exit $$EXIT_CODE

mykg-status: .venv/bin/activate
	@.venv/bin/python .agents/skills/iqoqo-mykg/scripts/get_status.py

mykg-ask: .venv/bin/activate
	@if [ -z "$(Q)" ]; then \
		echo "Usage: make mykg-ask Q=\"<question>\""; \
		exit 1; \
	fi
	@.venv/bin/python .agents/skills/iqoqo-mykg/scripts/ask.py "$(Q)"

# Graphify targets
graphify-update: .venv/bin/activate
	$(AI_ECHO) "Running autonomous graphify update..."
	@.venv/bin/python .agents/skills/iqoqo-graphify/scripts/run_update.py

graphify-index: .venv/bin/activate
	$(AI_ECHO) "Running full graphify index..."
	@.venv/bin/python .agents/skills/iqoqo-graphify/scripts/run_index.py

graphify-status: .venv/bin/activate
	@.venv/bin/python .agents/skills/iqoqo-graphify/scripts/get_status.py

# Session sync: converts agy JSONL transcripts to Markdown before knowledge tools mine them.
# Single-loop: scans brain dirs, filters to VERSION-matching sessions only, converts to MD.
# Also auto-patches .iqoqo-mykg-scope.yaml so the ai-memory version pin stays current.
# No external tools required — script lives in scripts/sync_agy_memory.sh.
memory-presync:
	$(AI_ECHO) "Syncing agy session transcripts → .context/ai-memory/$(IQOQO_VERSION)..."
	@bash scripts/sync_agy_memory.sh $(IQOQO_VERSION)
	$(AI_ECHO) "Patching .iqoqo-mykg-scope.yaml ai-memory version → $(IQOQO_VERSION)..."
	@sed -i 's|\.context/ai-memory/[0-9][0-9.]*|.context/ai-memory/$(IQOQO_VERSION)|g' .iqoqo-mykg-scope.yaml

# Fast knowledge sync: session presync followed by fast local engines only (<45s, 0 LLM tokens).
# Safe to run automatically during interactive sessions and post-commit hooks.
knowledge-sync: memory-presync
	$(AI_ECHO) "Syncing fast knowledge engines in parallel (CodeGraph + Graphify)..."
	@$(MAKE) -j2 codegraph-sync graphify-update
	$(AI_ECHO) "Fast knowledge sync complete. (Full MemPalace & myKG sync available via 'make knowledge-sync-full')."

# Full knowledge sync: fast sync followed by heavy MemPalace (~15 min hallway walk) and myKG LLM daemon.
# For scheduled release CI or manual off-peak execution. Strictly prohibited from automated session calls.
knowledge-sync-full: knowledge-sync
	$(AI_ECHO) "Running heavy knowledge engines in parallel (MemPalace + myKG)..."
	@$(MAKE) -j2 mempalace-index mykg-update
	$(AI_ECHO) "All knowledge engines fully synced."


bump-version: .venv/bin/activate
	@if [ -z "$(v)" ]; then \
		echo "Usage: make bump-version v=major|minor|patch"; \
		exit 1; \
	fi
	@echo "Bumping version ($(v))..."
	@.venv/bin/python scripts/sync_version.py --bump $(v)

.venv/bin/activate: requirements.txt
	@set -e; \
		if [ ! -d ".venv" ]; then \
			if [ "$(IQOQO_AI_MODE)" != "1" ]; then echo "🔧 Creating virtual environment..."; fi; \
			python3 -m venv .venv; \
		fi; \
		if [ "$(IQOQO_AI_MODE)" = "1" ]; then \
			if ! .venv/bin/pip install black ruff mypy isort >.venv/requirements-install.log 2>&1; then \
				.venv/bin/python -c "from pathlib import Path; print(Path('.venv/requirements-install.log').read_text(), end='')"; \
				exit 1; \
			fi; \
			if ! .venv/bin/pip install -r requirements.txt >.venv/requirements-install.log 2>&1; then \
				.venv/bin/python -c "from pathlib import Path; print(Path('.venv/requirements-install.log').read_text(), end='')"; \
				exit 1; \
			fi; \
			rm -f .venv/requirements-install.log; \
		else \
			echo "🔧 Syncing python dependencies..."; \
			.venv/bin/pip install black ruff mypy isort; \
			.venv/bin/pip install -r requirements.txt; \
		fi; \
		touch .venv/bin/activate

# Development targets
init: .venv/bin/activate
	@echo "Initializing development environment..."
	cd frontend && npm install

# Mode detection has been moved to the top of the Makefile

PREBUILT_FLAG =
ifeq ($(filter prebuilt,$(MAKECMDGOALS)),prebuilt)
  PREBUILT_FLAG = --prebuilt
endif

.PHONY: preview prod dev prebuilt clone

preview:
	@:
prod:
	@:
dev:
	@:
prebuilt:
	@:

clone:
	@if [ -z "$(src_loc)" ] || [ -z "$(src_name)" ] || [ -z "$(dst_loc)" ] || [ -z "$(dst_name)" ]; then \
		echo "Usage: make clone [src_host=<source_host>] src_loc=<source_location> src_name=<source_name> dst_loc=<destination_location> dst_name=<destination_name>"; \
		echo "Example (local): make clone src_loc=/opt/iqoqo.cc src_name=prod dst_loc=/opt/pre.iqoqo.cc dst_name=preview"; \
		echo "Example (remote): make clone src_host=user@remote-ip src_loc=/opt/iqoqo.cc src_name=prod dst_loc=/opt/pre.iqoqo.cc dst_name=preview"; \
		exit 1; \
	fi
	FORCE="$(FORCE)" ./scripts/clone.sh "$(src_loc)" "$(src_name)" "$(dst_loc)" "$(dst_name)" "$(src_host)"

ifeq ($(filter prebuilt,$(MAKECMDGOALS)),prebuilt)
start:
	@mkdir -p $(HOME)/.config/rclone && touch $(HOME)/.config/rclone/rclone.conf
	@echo "Deploying $(COMPOSE_PROJECT) (prebuilt)..."
	@echo "Project version: $(IQOQO_VERSION)"
	@echo "Prebuilt tag: $(PREBUILT_TAG)"
	@docker image prune -f --filter "dangling=true"
	@if [ -n "$(IMAGE_PREFIX)" ]; then \
		IMAGE_PREFIX="$(IMAGE_PREFIX)" COMPOSE_PROJECT_NAME=$(COMPOSE_PROJECT) APP_VERSION=$(PREBUILT_TAG) docker compose $(if $(wildcard $(COMPOSE_ENV_FILE)),--env-file $(COMPOSE_ENV_FILE),) -f docker-compose.prebuilt.yml pull; \
	fi
	@IMAGE_PREFIX="$(IMAGE_PREFIX)" COMPOSE_PROJECT_NAME=$(COMPOSE_PROJECT) APP_VERSION=$(PREBUILT_TAG) docker compose $(if $(wildcard $(COMPOSE_ENV_FILE)),--env-file $(COMPOSE_ENV_FILE),) -f docker-compose.prebuilt.yml up -d
else
start:
	@mkdir -p $(HOME)/.config/rclone && touch $(HOME)/.config/rclone/rclone.conf
	@echo "Starting $(MODE) environment..."
	@./run.sh $(MODE) $(PREBUILT_FLAG) $(args)
endif

version:
	@echo "Project version: $(IQOQO_VERSION)"
	@echo "Prebuilt tag: $(PREBUILT_TAG)"

stop:
	@echo "Stopping $(MODE) environment..."
	@./run.sh $(MODE) --stop

.PHONY: docker-build docker-build-preview
docker-build: ## Build backend, frontend, and nginx Docker images locally (TAG defaults to pyproject.toml version)
	@./scripts/build_docker_images.sh $(if $(TAG),--tag $(TAG),) $(if $(PREFIX),--prefix $(PREFIX),)

docker-build-preview: ## Build all images locally tagged for preview environment (preview tag)
	@./scripts/build_docker_images.sh --tag preview $(if $(PREFIX),--prefix $(PREFIX),)

# monitoring-start and monitoring-stop removed — the monitoring stack is now
# always composed together with the main stack via run.sh (line 751-754).
# Use `make start <mode>` and `make stop` to manage the full lifecycle.


status: ## Show health status of all iQoQo services
	@bash scripts/iqoqo-status.sh $(if $(filter preview,$(MAKECMDGOALS)),--stack preview,$(if $(filter prod,$(MAKECMDGOALS)),--stack prod,$(if $(filter dev,$(MAKECMDGOALS)),--stack dev,$(if $(STACK),--stack $(STACK),$(if $(STAGE),--stack $(STAGE),--stack $(MODE))))))

# Linting targets
lint-python: .venv/bin/activate
	$(AI_ECHO) "Running ruff..."
	.venv/bin/ruff check $(RUFF_FLAGS) app/ tests/ scripts/
	$(AI_ECHO) "Running mypy..."
	rm -rf .mypy_cache || true
	.venv/bin/mypy $(MYPY_FLAGS) app/ tests/
	$(AI_ECHO) "Running pylint..."
	.venv/bin/pylint $(PYLINT_FLAGS) app/ tests/ scripts/

lint-format: .venv/bin/activate
	$(AI_ECHO) "Checking Python formatting..."
	.venv/bin/black --check app/ tests/ scripts/
	.venv/bin/isort --check-only app/ tests/ scripts/

lint-js:
	$(AI_ECHO) "Running eslint..."
	@cd frontend && $(NPM) run lint

lint-ts:
	$(AI_ECHO) "Running TypeScript type checks..."
	@cd frontend && $(NPX) tsc --noEmit

lint-frontend: lint-js lint-ts

build-frontend:
	@echo "Building Next.js production bundle..."
	@cd frontend && npm run build

lint-license:
	$(AI_ECHO) "Checking copyright headers..."
	./scripts/check_license.sh

lint-css:
	$(AI_ECHO) "Running stylelint..."
	$(NPX) stylelint --allow-empty-input "frontend/app/**/*.css" "frontend/components/**/*.css"

lint-markdown:
	$(AI_ECHO) "Running markdownlint..."
	$(NPX) markdownlint-cli2 "**/*.md" "#node_modules" "#.venv" "#frontend/node_modules" "#frontend/.next" "#.github" "#.pytest_cache" "#.agents" "#.gemini" "#frontend/playwright-report" "#frontend/test-results" "#.caim" "#.context" "#graphify-out" "#openspec/changes"

validate-yaml: .venv/bin/activate
	$(AI_ECHO) "Checking YAML configuration files..."
	@.venv/bin/python scripts/validate_yaml.py

# Compatibility baseline: executable checks that gate .github/workflows/quality.yml.
lint: .venv/bin/activate
	@PATH="$(NODE_DIR):$$PATH" .venv/bin/python scripts/run_lint.py

# Stricter checks that are intentionally not part of the existing CI baseline.
lint-all: .venv/bin/activate
	@PATH="$(NODE_DIR):$$PATH" .venv/bin/python scripts/run_lint.py --all

# Formatting targets
format-python: .venv/bin/activate
	@echo "Formatting Python code..."
	.venv/bin/black app/ tests/ scripts/
	.venv/bin/isort app/ tests/ scripts/

format-js:
	@echo "Formatting frontend TypeScript and CSS..."
	@cd frontend && $(NPX) prettier --write "**/*.{ts,tsx,css}" --ignore-path .gitignore

format: format-python format-js
	@echo "All code formatted!"

# Testing
test-backend: .venv/bin/activate
	$(AI_ECHO) "Running backend tests..."
	.venv/bin/pytest tests/

test-backend-pg: .venv/bin/activate
	@echo "Running PostgreSQL-dependent integration tests against iqoqo_test..."
	@echo "Ensuring test database exists..."
	@psql "postgresql://iqoqo:changeme_strong_password@localhost:5432/postgres" \
		-tc "SELECT 1 FROM pg_database WHERE datname='iqoqo_test'" 2>/dev/null \
		| grep -q 1 \
		&& echo "iqoqo_test already exists." \
		|| (psql "postgresql://iqoqo:changeme_strong_password@localhost:5432/postgres" \
			-c "CREATE DATABASE iqoqo_test" && echo "Created iqoqo_test.")
	ENABLE_FTS_TESTS=true \
	DATABASE_URL=postgresql://iqoqo:changeme_strong_password@localhost:5432/iqoqo_test \
	$(MAKE) pg-create-schemas
	ENABLE_FTS_TESTS=true \
	DATABASE_URL=postgresql://iqoqo:changeme_strong_password@localhost:5432/iqoqo_test \
	.venv/bin/pytest tests/integration/db/ -v

test-frontend:
	$(AI_ECHO) "Running frontend unit tests (Vitest)..."
	cd frontend && $(NPM) run test

test-scripts-bash:
	$(AI_ECHO) "Running BATS script tests..."
	@if command -v bats >/dev/null 2>&1; then \
		bats tests/bash/; \
	elif [ -f node_modules/.bin/bats ]; then \
		$(NPX) bats tests/bash/; \
	else \
		echo "Error: bats is not installed. Please install bats-core or run 'npm install'."; \
		exit 1; \
	fi

test-scripts-python: .venv/bin/activate
	$(AI_ECHO) "Running Python script logic tests..."
	.venv/bin/pytest tests/test_scripts.py tests/test_script_utilities.py

# Helper: ensure PostgreSQL schemas exist before db.create_all() runs.
# Safe to call on SQLite (psql not installed; the app creates public only).
pg-create-schemas:
	@if command -v psql > /dev/null 2>&1 && echo "$$DATABASE_URL" | grep -q 'postgresql'; then \
		echo "Creating PostgreSQL schemas (auth, catalog, inventory, social) if missing..."; \
		psql "$$DATABASE_URL" -c "CREATE SCHEMA IF NOT EXISTS auth;" 2>&1 | grep -v 'already exists' || true; \
		psql "$$DATABASE_URL" -c "CREATE SCHEMA IF NOT EXISTS catalog;" 2>&1 | grep -v 'already exists' || true; \
		psql "$$DATABASE_URL" -c "CREATE SCHEMA IF NOT EXISTS inventory;" 2>&1 | grep -v 'already exists' || true; \
		psql "$$DATABASE_URL" -c "CREATE SCHEMA IF NOT EXISTS social;" 2>&1 | grep -v 'already exists' || true; \
	fi

# This dedicated Compose file/project has its own PostgreSQL service, port, and
# project-scoped volume. No default, preview, or production stack is referenced.
override E2E_COMPOSE := docker compose --project-name iqoqo-e2e-test -f docker-compose.e2e.yml
E2E_DATABASE_URL = postgresql://iqoqo_e2e:e2e_local_only@127.0.0.1:55432/iqoqo_e2e_test
E2E_SELECTED_DATABASE_URL = $(if $(DATABASE_URL_TEST),$(DATABASE_URL_TEST),$(E2E_DATABASE_URL))
export E2E_SELECTED_DATABASE_URL

# Preflight checks the selected URL and rendered Compose isolation before startup.
test-e2e-db-up: .venv/bin/activate
	@set -euo pipefail; \
		.venv/bin/python scripts/e2e_db_guard.py preflight --database-url "$$E2E_SELECTED_DATABASE_URL" --compose-project iqoqo-e2e-test --compose-file docker-compose.e2e.yml; \
		echo "Starting only the isolated E2E PostgreSQL service..."; \
		$(E2E_COMPOSE) up -d e2e-db; \
		for i in $$(seq 1 45); do \
			if $(E2E_COMPOSE) exec -T e2e-db pg_isready -U iqoqo_e2e -d iqoqo_e2e_test >/dev/null 2>&1; then break; fi; \
			if [ "$$i" = 45 ]; then echo "ERROR: isolated E2E PostgreSQL did not become ready." >&2; exit 1; fi; \
			sleep 1; \
		done; \
		.venv/bin/python scripts/e2e_db_guard.py verify-running --database-url "$$E2E_SELECTED_DATABASE_URL" --compose-project iqoqo-e2e-test --compose-file docker-compose.e2e.yml

test-e2e: test-e2e-db-up
	@$(MAKE) --no-print-directory _test-e2e-run NO_RESET='$(NO_RESET)' args='$(args)'

# Internal: verify runtime identity immediately before reset and again before
# Playwright startup. set -e makes every failed prepare step fail closed.
_test-e2e-run:
	@set -euo pipefail; \
		.venv/bin/python scripts/e2e_db_guard.py verify-running --database-url "$$E2E_SELECTED_DATABASE_URL" --compose-project iqoqo-e2e-test --compose-file docker-compose.e2e.yml; \
		if [ -z '$(NO_RESET)' ]; then \
			echo "Resetting the verified dedicated E2E database..."; \
			DATABASE_URL="$$E2E_SELECTED_DATABASE_URL" psql "$$E2E_SELECTED_DATABASE_URL" -v ON_ERROR_STOP=1 -c 'CREATE SCHEMA IF NOT EXISTS auth' -c 'CREATE SCHEMA IF NOT EXISTS catalog' -c 'CREATE SCHEMA IF NOT EXISTS inventory' -c 'CREATE SCHEMA IF NOT EXISTS social'; \
			DATABASE_URL="$$E2E_SELECTED_DATABASE_URL" ADMIN_EMAIL=ci-admin@iqoqo.cc ADMIN_PASSWORD=E2EBootstrapPassword123! PYTHONPATH=. .venv/bin/python scripts/init_db.py --seed-file data/seed_example.json --reset --force; \
			DATABASE_URL="$$E2E_SELECTED_DATABASE_URL" SECRET_KEY=test-secret-key-not-for-production ADMIN_EMAIL=ci-admin@iqoqo.cc ADMIN_PASSWORD=E2EBootstrapPassword123! PYTHONPATH=. .venv/bin/python scripts/init_auth.py; \
			DATABASE_URL="$$E2E_SELECTED_DATABASE_URL" PYTHONPATH=. .venv/bin/python tests/e2e/scripts/seed_e2e.py; \
		else echo "Skipping E2E database reset (NO_RESET=1); isolated target identity was still verified."; fi; \
		.venv/bin/python scripts/e2e_db_guard.py verify-running --database-url "$$E2E_SELECTED_DATABASE_URL" --compose-project iqoqo-e2e-test --compose-file docker-compose.e2e.yml; \
		IQOQO_E2E_NEXT_DIST_DIR=".next-e2e-$${UID}-$$"; export IQOQO_E2E_NEXT_DIST_DIR; \
		echo "Running Playwright against the verified isolated E2E database..."; \
		cd frontend; FLASK_API_URL=http://127.0.0.1:5002/api DATABASE_URL_TEST="$$E2E_SELECTED_DATABASE_URL" CI=true ADMIN_EMAIL=ci-admin@iqoqo.cc ADMIN_PASSWORD=E2EBootstrapPassword123! SECRET_KEY=test-secret-key-not-for-production $(NPX) playwright test --project=chromium $(args)


test: test-backend test-frontend test-scripts-bash test-scripts-python test-e2e
	$(AI_ECHO) "All tests completed!"

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
db-init: .venv/bin/activate
	@echo "Initializing database with seed data..."
	.venv/bin/python scripts/init_db.py --seed-file data/seed_example.json

db-seed: .venv/bin/activate
	@echo "Loading seed data..."
	.venv/bin/python scripts/init_db.py --seed-file data/seed_example.json

db-seed-e2e: .venv/bin/activate
	@echo "Loading E2E specific seed data..."
	PYTHONPATH=. .venv/bin/python tests/e2e/scripts/seed_e2e.py

db-export: .venv/bin/activate
	@echo "Exporting database to exports/backup.json..."
	@$(PYTHON_CMD) -c "exec(\"from app import create_app\nfrom app.core.data_manager import DataManager\napp = create_app()\nwith app.app_context():\n DataManager.export_to_file('exports/backup.json')\")"
	@docker compose -p $(COMPOSE_PROJECT) cp web:/usr/src/app/exports/backup.json ./exports/backup.json 2>/dev/null || true
	@echo "Export complete: exports/backup.json"

migrate-secrets: .venv/bin/activate
	@echo "Migrating API secrets from .env into encrypted database settings..."
	.venv/bin/python scripts/migrate_env_secrets_to_db.py $(args)

backup-run:
	@if [ -z "$(remote)" ]; then \
		echo "Usage: make backup-run remote=<rclone_remote_name>"; \
		echo "  Example: make backup-run remote=iqoqo-backup"; \
		exit 1; \
	fi
	@cd $(CURDIR) && bash scripts/cloud_backup.sh $(remote)

backup-install: backup-run
	@bash scripts/cloud_backup_cron.sh install $(remote)

backup-uninstall:
	@bash scripts/cloud_backup_cron.sh uninstall

backup-check:
	@bash scripts/cloud_backup_check.sh $(remote)

db-reset: pg-create-schemas .venv/bin/activate
	@echo "Resetting database..."
	.venv/bin/python scripts/init_db.py --seed-file data/seed_example.json --reset

db-stamp: .venv/bin/activate
	@echo "Stamping database migration version to head..."
	@if [ "$(USE_DOCKER)" = "true" ]; then \
		ENV_FILE=$(COMPOSE_ENV_FILE) docker compose -p $(COMPOSE_PROJECT) -f $(COMPOSE_FILE) --env-file $(COMPOSE_ENV_FILE) exec -T web flask db stamp head; \
	else \
		PYTHONPATH=. .venv/bin/flask db stamp head; \
	fi

db-upgrade: .venv/bin/activate
	@echo "Upgrading database schema to head..."
	@if [ "$(USE_DOCKER)" = "true" ]; then \
		ENV_FILE=$(COMPOSE_ENV_FILE) docker compose -p $(COMPOSE_PROJECT) -f $(COMPOSE_FILE) --env-file $(COMPOSE_ENV_FILE) exec -T web flask db upgrade; \
	else \
		PYTHONPATH=. .venv/bin/flask db upgrade; \
	fi

init-auth: .venv/bin/activate
	@echo "Initializing auth (roles, permissions, admin user)..."
	ADMIN_PASSWORD=admin PYTHONPATH=. .venv/bin/python scripts/init_auth.py

db-stats: .venv/bin/activate
	@echo "Database statistics:"
	@$(PYTHON_CMD) -c "exec(\"from app import create_app\nfrom app.core.data_manager import DataManager\napp = create_app()\nwith app.app_context():\n stats = DataManager.get_stats()\n print('  Works:', stats['works'])\n print('  Expressions:', stats['expressions'])\n print('  Manifestations:', stats['manifestations'])\n print('  Items:', stats['items'])\n print('  Total:', sum(stats.values()))\")"

sync-permissions: .venv/bin/activate
	@echo "Synchronizing permissions (Code & Database)..."
	@PYTHONPATH=. .venv/bin/python scripts/sync_permissions.py
	@PYTHONPATH=. .venv/bin/python scripts/sync_db_permissions.py
	@echo "Permissions synchronized successfully."

verify-perms: .venv/bin/activate
	@echo "Verifying permissions are synchronized"
	.venv/bin/python scripts/sync_permissions.py --verify

retry-missing-covers: .venv/bin/activate
	@echo "Retrying missing covers in $(MODE) environment..."
	@if [ "$(USE_DOCKER)" = "true" ]; then \
		$(PYTHON_CMD) scripts/retry_missing_covers.py $(if $(limit),--limit $(limit),); \
	else \
		if [ -f ".env" ]; then \
			set -a; . ./.env; set +a; \
		fi; \
		if [ -f ".env.$(MODE)" ]; then \
			set -a; . ./.env.$(MODE); set +a; \
		fi; \
		export DATABASE_URL=$$(echo "$$DATABASE_URL" | sed "s/@db:5432/@localhost:$${DB_PORT:-5432}/" | sed "s/@db:/@localhost:/"); \
		export REDIS_URL=$$(echo "$$REDIS_URL" | sed "s/:\/\/redis:6379/:\/\/localhost:$${REDIS_PORT:-6379}/" | sed "s/:\/\/redis/:\/\/localhost/"); \
		$(PYTHON_CMD) scripts/retry_missing_covers.py $(if $(limit),--limit $(limit),); \
	fi

fetch-covers: .venv/bin/activate
	@echo "Fetching missing covers in $(MODE) environment..."
	@if [ "$(USE_DOCKER)" = "true" ]; then \
		$(PYTHON_CMD) scripts/fetch_covers.py $(if $(limit),--limit $(limit),) $(if $(force),--force,); \
	else \
		if [ -f ".env" ]; then \
			set -a; . ./.env; set +a; \
		fi; \
		if [ -f ".env.$(MODE)" ]; then \
			set -a; . ./.env.$(MODE); set +a; \
		fi; \
		export DATABASE_URL=$$(echo "$$DATABASE_URL" | sed "s/@db:5432/@localhost:$${DB_PORT:-5432}/" | sed "s/@db:/@localhost:/"); \
		export REDIS_URL=$$(echo "$$REDIS_URL" | sed "s/:\/\/redis:6379/:\/\/localhost:$${REDIS_PORT:-6379}/" | sed "s/:\/\/redis/:\/\/localhost/"); \
		$(PYTHON_CMD) scripts/fetch_covers.py $(if $(limit),--limit $(limit),) $(if $(force),--force,); \
	fi

refetch-metadata: .venv/bin/activate
	@echo "Refetching missing metadata in $(MODE) environment..."
	@if [ "$(USE_DOCKER)" = "true" ]; then \
		$(PYTHON_CMD) scripts/refetch_metadata.py $(if $(gap),--gap $(gap),) $(if $(content-type),--content-type $(content-type),) $(if $(limit),--limit $(limit),) $(if $(force),--force,) $(if $(dry-run),--dry-run,); \
	else \
		if [ -f ".env" ]; then \
			set -a; . ./.env; set +a; \
		fi; \
		if [ -f ".env.$(MODE)" ]; then \
			set -a; . ./.env.$(MODE); set +a; \
		fi; \
		export DATABASE_URL=$$(echo "$$DATABASE_URL" | sed "s/@db:5432/@localhost:$${DB_PORT:-5432}/" | sed "s/@db:/@localhost:/"); \
		export REDIS_URL=$$(echo "$$REDIS_URL" | sed "s/:\/\/redis:6379/:\/\/localhost:$${REDIS_PORT:-6379}/" | sed "s/:\/\/redis/:\/\/localhost/"); \
		$(PYTHON_CMD) scripts/refetch_metadata.py $(if $(gap),--gap $(gap),) $(if $(content-type),--content-type $(content-type),) $(if $(limit),--limit $(limit),) $(if $(force),--force,) $(if $(dry-run),--dry-run,); \
	fi

allegro-auth: .venv/bin/activate
	@$(PYTHON_CMD) scripts/allegro_auth.py

fix-physical-kinds: .venv/bin/activate
	@echo "Running fix-physical-kinds script in $(MODE) environment..."
	@if [ "$(USE_DOCKER)" = "true" ]; then \
		$(PYTHON_CMD) scripts/fix_physical_kinds.py $(ARGS); \
	else \
		if [ -f ".env" ]; then \
			set -a; . ./.env; set +a; \
		fi; \
		if [ -f ".env.$(MODE)" ]; then \
			set -a; . ./.env.$(MODE); set +a; \
		fi; \
		export DATABASE_URL=$$(echo "$$DATABASE_URL" | sed "s/@db:5432/@localhost:$${DB_PORT:-5432}/" | sed "s/@db:/@localhost:/"); \
		export REDIS_URL=$$(echo "$$REDIS_URL" | sed "s/:\/\/redis:6379/:\/\/localhost:$${REDIS_PORT:-6379}/" | sed "s/:\/\/redis/:\/\/localhost/"); \
		$(PYTHON_CMD) scripts/fix_physical_kinds.py $(ARGS); \
	fi

## AI Cover Automation
generate-covers: ## Run AI cover generation batch for unwatermarked items
	$(PYTHON_CMD) scripts/generate_ai_covers.py --batch-all-unwatermarked

generate-covers-dry: ## Dry-run AI cover generation batch
	$(PYTHON_CMD) scripts/generate_ai_covers.py --batch-all-unwatermarked --dry-run

watermark-covers: ## Apply watermarks to existing AI covers without regenerating
	$(PYTHON_CMD) scripts/generate_ai_covers.py --batch-all-unwatermarked --watermark-only

## Semantic Web / Ontology
audit-frbr: ## Running FRBR integrity audit (USE_DOCKER=true for production)
	@echo "Running FRBR integrity audit..."
	@if [ "$(USE_DOCKER)" = "true" ]; then \
		ENV_FILE=$(COMPOSE_ENV_FILE) docker compose -p $(COMPOSE_PROJECT) -f $(COMPOSE_FILE) --env-file $(COMPOSE_ENV_FILE) exec -T -e DATABASE_URL=$$(grep '^DATABASE_URL=' $(COMPOSE_ENV_FILE) | cut -d'=' -f2- | sed 's/"//g' | sed 's/@localhost:/@db:/') web env PYTHONPATH=. python scripts/audit_frbr_integrity.py $(ARGS); \
	else \
		if [ -f ".env" ]; then \
			set -a; . ./.env; set +a; \
		fi; \
		export DATABASE_URL=$$(echo "$$DATABASE_URL" | sed "s/@db:5432/@localhost:$${DB_PORT:-5432}/" | sed "s/@db:/@localhost:/"); \
		export REDIS_URL=$$(echo "$$REDIS_URL" | sed "s/:\/\/redis:6379/:\/\/localhost:$${REDIS_PORT:-6379}/" | sed "s/:\/\/redis/:\/\/localhost/"); \
		$(PYTHON_CMD) scripts/audit_frbr_integrity.py $(ARGS); \
	fi

etl-frbr: ## Running FRBR ETL strict cleanup (idempotent, USE_DOCKER=true for production)
	@echo "Running FRBR ETL strict cleanup (idempotent)..."
	@if [ "$(USE_DOCKER)" = "true" ]; then \
		ENV_FILE=$(COMPOSE_ENV_FILE) docker compose -p $(COMPOSE_PROJECT) -f $(COMPOSE_FILE) --env-file $(COMPOSE_ENV_FILE) exec -T -e DATABASE_URL=$$(grep '^DATABASE_URL=' $(COMPOSE_ENV_FILE) | cut -d'=' -f2- | sed 's/"//g' | sed 's/@localhost:/@db:/') web env PYTHONPATH=. python scripts/etl_frbr_strict.py $(ARGS); \
	else \
		if [ -f ".env" ]; then \
			set -a; . ./.env; set +a; \
		fi; \
		export DATABASE_URL=$$(echo "$$DATABASE_URL" | sed "s/@db:5432/@localhost:$${DB_PORT:-5432}/" | sed "s/@db:/@localhost:/"); \
		export REDIS_URL=$$(echo "$$REDIS_URL" | sed "s/:\/\/redis:6379/:\/\/localhost:$${REDIS_PORT:-6379}/" | sed "s/:\/\/redis/:\/\/localhost/"); \
		$(PYTHON_CMD) scripts/etl_frbr_strict.py $(ARGS); \
	fi

sync-ontology: ## Checking ontology sync with DB models (USE_DOCKER=true for production)
	@echo "Checking ontology sync with DB models..."
	@if [ "$(USE_DOCKER)" = "true" ]; then \
		ENV_FILE=$(COMPOSE_ENV_FILE) docker compose -p $(COMPOSE_PROJECT) -f $(COMPOSE_FILE) --env-file $(COMPOSE_ENV_FILE) exec -T -e DATABASE_URL=$$(grep '^DATABASE_URL=' $(COMPOSE_ENV_FILE) | cut -d'=' -f2- | sed 's/"//g' | sed 's/@localhost:/@db:/') web env PYTHONPATH=. python scripts/sync_ontology.py $(ARGS); \
	else \
		if [ -f ".env" ]; then \
			set -a; . ./.env; set +a; \
		fi; \
		export DATABASE_URL=$$(echo "$$DATABASE_URL" | sed "s/@db:5432/@localhost:$${DB_PORT:-5432}/" | sed "s/@db:/@localhost:/"); \
		export REDIS_URL=$$(echo "$$REDIS_URL" | sed "s/:\/\/redis:6379/:\/\/localhost:$${REDIS_PORT:-6379}/" | sed "s/:\/\/redis/:\/\/localhost/"); \
		$(PYTHON_CMD) scripts/sync_ontology.py $(ARGS); \
	fi

.PHONY: help start stop lint lint-python lint-format lint-js lint-ts lint-css lint-markdown lint-frontend format format-python format-js test test-phase2 clean db-init db-seed db-export db-stats build-frontend

help:
	@echo "Available targets:"
	@echo ""
	@echo "Development:"
	@echo "  start         - Start development environment (DB, Flask API, Next.js frontend)"
	@echo "  stop          - Stop all development servers and containers"
	@echo ""
	@echo "Code quality:"
	@echo "  lint          - Run all linting checks"
	@echo "  lint-python   - Run Python linters (ruff, mypy, pylint)"
	@echo "  lint-format   - Check Python code formatting (black)"
	@echo "  lint-js       - Run legacy JavaScript linter (eslint)"
	@echo "  lint-frontend - Run Next.js / TypeScript linter"
	@echo "  lint-css      - Run CSS linter (stylelint)"
	@echo "  lint-markdown - Run Markdown linter"
	@echo "  format        - Format all code"
	@echo "  format-python - Format Python code (black, isort)"
	@echo "  format-js     - Format JavaScript code (prettier)"
	@echo "  test          - Run all backend tests"
	@echo "  test-phase2   - Run Phase 2 API integration tests"
	@echo "  build-frontend - Build Next.js production bundle"
	@echo "  clean         - Remove build artifacts"
	@echo ""
	@echo "Database targets:"
	@echo "  db-init       - Initialize database with seed data"
	@echo "  db-seed       - Load seed data into existing database"
	@echo "  db-export     - Export database to data/backup.json"
	@echo "  db-stats      - Show database statistics"

# Development targets
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
	@docker-compose stop
	@echo "Development environment stopped."

# Linting targets
lint-python:
	@echo "Running ruff..."
	.venv/bin/ruff check app/ tests/ scripts/
	@echo "Running mypy..."
	.venv/bin/mypy app/ tests/
	@echo "Running pylint..."
	.venv/bin/pylint app/ tests/ scripts/

lint-format:
	@echo "Checking Python formatting..."
	.venv/bin/black --check app/ tests/ scripts/
	.venv/bin/isort --check-only app/ tests/ scripts/

lint-js:
	@echo "Running eslint..."
	@cd frontend && npm run lint

lint-ts:
	@echo "Running TypeScript type checks..."
	@cd frontend && npx tsc --noEmit

lint-frontend: lint-js lint-ts

build-frontend:
	@echo "Building Next.js production bundle..."
	@cd frontend && npm run build

lint-css:
	@echo "Running stylelint..."
	npx stylelint --allow-empty-input "frontend/app/**/*.css" "frontend/components/**/*.css"

lint-markdown:
	@echo "Running markdownlint..."
	npx markdownlint-cli2 "**/*.md" "#node_modules" "#.venv" "#frontend/node_modules"

# Run all linting checks (stops on first failure)
lint: lint-python lint-format lint-js lint-ts lint-css lint-markdown
	@echo "All linting checks passed!"

# Formatting targets
format-python:
	@echo "Formatting Python code..."
	.venv/bin/black app/ tests/ scripts/
	.venv/bin/isort app/ tests/ scripts/

format-js:
	@echo "Formatting frontend TypeScript and CSS..."
	@cd frontend && npx prettier --write "**/*.{ts,tsx,css}" --ignore-path .gitignore

format: format-python format-js
	@echo "All code formatted!"

# Testing
test:
	.venv/bin/pytest tests/

test-phase2:
	.venv/bin/pytest tests/test_phase2_frontend.py -v

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

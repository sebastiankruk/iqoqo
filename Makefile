.PHONY: help start stop lint lint-python lint-format lint-js lint-css lint-markdown format format-python format-js test clean db-init db-seed db-export db-stats

help:
	@echo "Available targets:"
	@echo ""
	@echo "Development:"
	@echo "  start         - Start development environment (Colima, PostgreSQL, Flask)"
	@echo "  stop          - Stop development environment"
	@echo ""
	@echo "Code quality:"
	@echo "  lint          - Run all linting checks"
	@echo "  lint-python   - Run Python linters (ruff, mypy)"
	@echo "  lint-format   - Check Python code formatting (black)"
	@echo "  lint-js       - Run JavaScript linter (eslint)"
	@echo "  lint-css      - Run CSS linter (stylelint)"
	@echo "  lint-markdown - Run Markdown linter"
	@echo "  format        - Format all code"
	@echo "  format-python - Format Python code (black, isort)"
	@echo "  format-js     - Format JavaScript code (prettier)"
	@echo "  test          - Run tests"
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
	@pkill -f "flask run" || true
	@echo "Stopping database..."
	@docker-compose down
	@echo "Development environment stopped."

# Linting targets
lint-python:
	@echo "Running ruff..."
	ruff check app/ tests/ scripts/
	@echo "Running mypy..."
	mypy app/ tests/
	@echo "Running pylint..."
	pylint app/ tests/ scripts/

lint-format:
	@echo "Checking Python formatting..."
	black --check app/ tests/ scripts/
	isort --check-only app/ tests/ scripts/

lint-js:
	@echo "Running eslint..."
	npx eslint app/web/static/js/**/*.js

lint-css:
	@echo "Running stylelint..."
	npx stylelint "app/web/static/css/**/*.css"

lint-markdown:
	@echo "Running markdownlint..."
	npx markdownlint-cli2 "**/*.md" "!node_modules" "!.venv"

# Run all linting checks (stops on first failure)
lint: lint-python lint-format lint-js lint-css lint-markdown
	@echo "All linting checks passed!"

# Formatting targets
format-python:
	@echo "Formatting Python code..."
	black app/ tests/ scripts/
	isort app/ tests/ scripts/

format-js:
	@echo "Formatting JavaScript and CSS..."
	npx prettier --write "app/web/static/js/**/*.js"
	npx prettier --write "app/web/static/css/**/*.css"

format: format-python format-js
	@echo "All code formatted!"

# Testing
test:
	pytest tests/

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
	python scripts/init_db.py --seed-file data/seed_example.json

db-seed:
	@echo "Loading seed data..."
	python scripts/init_db.py --seed-file data/seed_example.json

db-export:
	@echo "Exporting database to data/backup.json..."
	@python -c "from app import create_app; from app.core.data_manager import DataManager; \
		app = create_app(); \
		with app.app_context(): DataManager.export_to_file('data/backup.json')"
	@echo "Export complete: data/backup.json"

db-stats:
	@echo "Database statistics:"
	@python -c "from app import create_app; from app.core.data_manager import DataManager; \
		app = create_app(); \
		with app.app_context(): \
			stats = DataManager.get_stats(); \
			print(f\"  Works: {stats['works']}\"); \
			print(f\"  Expressions: {stats['expressions']}\"); \
			print(f\"  Manifestations: {stats['manifestations']}\"); \
			print(f\"  Items: {stats['items']}\"); \
			print(f\"  Total: {sum(stats.values())}\")"

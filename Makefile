.PHONY: help lint lint-python lint-format lint-js lint-css lint-markdown format format-python format-js test clean

help:
	@echo "Available targets:"
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

# Linting targets
lint-python:
	@echo "Running ruff..."
	ruff check app/ tests/ scripts/
	@echo "Running mypy..."
	mypy app/ tests/ scripts/

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

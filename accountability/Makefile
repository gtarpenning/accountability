.PHONY: dev-install lint format typecheck ruff check format-lint test test-watch

# Install development dependencies
dev-install:
	pip install -r requirements.txt
	pip install black pylint pytest mypy ruff pytest-cov pytest-asyncio httpx
	pip install -e .

# Run linting
lint:
	pip install pylint
	pylint accountability

# Format code using black
format:
	pip install black
	black accountability

# Type checking with mypy
typecheck:
	pip install mypy
	mypy accountability

# Add ruff linting command
ruff:
	pip install ruff
	ruff check accountability

# Run all checks (useful before committing)
check: format lint typecheck test ruff

# Format and lint code in sequence
format-lint:
	pip install black ruff pylint
	black accountability
	pylint accountability
	ruff check accountability --fix

# Run tests with coverage
test: dev-install
	pytest -v --cov=accountability --cov-report=term-missing

# Run tests in watch mode
test-watch: dev-install
	pytest -f -v --cov=accountability --cov-report=term-missing
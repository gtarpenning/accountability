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
	black .
	pylint .
	ruff check . --fix

# Run tests with coverage
test: dev-install
	pytest -v --cov=accountability --cov-report=term-missing

# Run tests in watch mode
test-watch: dev-install
	pytest -f -v --cov=accountability --cov-report=term-missing

.PHONY: install run-api run-frontend run dev clean

install:
	pip install -r requirements.txt
	pip install -e .

run-api:
	uvicorn main:app --reload --port 8000

run-frontend:
	pip install fastapi uvicorn
	streamlit run streamlit_app.py

# Run both services in parallel using background processes
run:
	streamlit run streamlit_app.py & \
	wait

# For development, install requirements and run services
dev: install run

# Clean up cache and temporary files
clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name ".mypy_cache" -exec rm -r {} +
	find . -type d -name ".ruff_cache" -exec rm -r {} + 
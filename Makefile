.PHONY: install run-api run-frontend run dev clean

install:
	pip install -r requirements.txt
	pip install -e .

run-api:
	uvicorn main:app --reload --port 8000

run-frontend:
	streamlit run streamlit_app.py

# Run both services in parallel using background processes
run:
	uvicorn accountability.main:app --reload --port 8000 & \
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
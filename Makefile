# PII Anonymizer API Makefile

.PHONY: help install test lint format clean run dev docker-build docker-run

# Default target
help:
	@echo "Available commands:"
	@echo "  install     - Install dependencies"
	@echo "  update-deps - Update dependencies"
	@echo "  test        - Run tests"
	@echo "  test-cov    - Run tests with coverage"
	@echo "  lint        - Run linting"
	@echo "  format      - Format code"
	@echo "  clean       - Clean up generated files"
	@echo "  run         - Run the application"
	@echo "  dev         - Run in development mode with auto-reload"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-run  - Run Docker container"

# Install dependencies
install:
	pip install -r requirements.txt
	python scripts/install_spacy_model.py

# Install dependencies without spaCy model (for CI/testing)
install-deps:
	pip install -r requirements.txt

update-deps:
	cat requirements.txt | grep -v '^#' | cut -f 1 -d '=' | xargs pip install -U

# Install spaCy model separately
install-spacy:
	python scripts/install_spacy_model.py

# Test presidio imports
test-presidio:
	python scripts/test_presidio_imports.py

# Check for dependency conflicts
check-deps:
	python scripts/check_dependencies.py

# Run tests
test:
	pytest

# Run simple tests only (no complex presidio imports)
test-simple:
	pytest tests/test_simple.py -v

# Run all tests with verbose output
test-verbose:
	pytest -v

# Run tests without warnings
test-quiet:
	python -W ignore::DeprecationWarning -m pytest

# Run simple tests without warnings
test-simple-quiet:
	python -W ignore::DeprecationWarning -m pytest tests/test_simple.py -v

# Run tests with coverage
test-cov:
	pytest --cov=main --cov-report=html --cov-report=term-missing

# Run specific test categories
test-unit:
	pytest -m "unit"

test-integration:
	pytest -m "integration"

test-performance:
	pytest -m "performance"

# Linting
lint:
	flake8 main.py tests/
	mypy main.py

# Format code
format:
	black main.py tests/
	isort main.py tests/

# Clean up
clean:
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .mypy_cache/
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

# Run application
run:
	uvicorn main:app --host 0.0.0.0 --port 8000

# Run in development mode
dev:
	uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Docker commands
docker-build:
	docker build -t pii-anonymizer-api .

docker-build-dev:
	docker build -f Dockerfile.dev -t pii-anonymizer-api:dev .

docker-run:
	docker run -p 8000:8000 pii-anonymizer-api

docker-run-dev:
	docker run -p 8000:8000 -v $(PWD):/app pii-anonymizer-api:dev

docker-clean:
	docker system prune -f
	docker image prune -f

# Development setup
setup-dev: install
	pre-commit install

# Check everything before commit
check: lint test

# Production deployment preparation
prepare-prod: format lint test-cov
	@echo "Production checks passed!"

# Install development dependencies
install-dev:
	pip install -r requirements.txt
	pip install pre-commit

# Generate API documentation
docs:
	@echo "API documentation available at:"
	@echo "  Swagger UI: http://localhost:8000/docs"
	@echo "  ReDoc: http://localhost:8000/redoc"

# Health check
health:
	curl -f http://localhost:8000/health || exit 1

# Load test (requires hey or similar tool)
load-test:
	@if command -v hey >/dev/null 2>&1; then \
		hey -n 100 -c 10 -m POST -H "Content-Type: application/json" \
		-d '{"text":"John Doe email is john@example.com"}' \
		http://localhost:8000/anonymize; \
	else \
		echo "Install 'hey' for load testing: go install github.com/rakyll/hey@latest"; \
	fi

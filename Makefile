.PHONY: help install install-dev test test-cov lint format typecheck clean all

help:
	@echo "COBOL Anonymizer - Development Commands"
	@echo ""
	@echo "Available commands:"
	@echo "  make install       - Install package"
	@echo "  make install-dev   - Install package with dev dependencies"
	@echo "  make test          - Run tests"
	@echo "  make test-cov      - Run tests with coverage report"
	@echo "  make lint          - Run ruff linter"
	@echo "  make format        - Format code with black"
	@echo "  make typecheck     - Run mypy type checker"
	@echo "  make clean         - Remove build artifacts and cache files"
	@echo "  make all           - Run format, lint, typecheck, and test"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

test:
	pytest

test-cov:
	pytest --cov-report=html

lint:
	ruff check src tests

format:
	black src tests --line-length 100

typecheck:
	mypy src

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

all: format lint typecheck test

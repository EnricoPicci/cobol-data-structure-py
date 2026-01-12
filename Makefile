.PHONY: help install install-dev test lint format typecheck clean all

help:
	@echo "Available commands:"
	@echo "  make install       - Install package"
	@echo "  make install-dev   - Install package with dev dependencies"
	@echo "  make test          - Run tests with coverage"
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

lint:
	ruff check src tests

format:
	black src tests

typecheck:
	mypy src

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

all: format lint typecheck test

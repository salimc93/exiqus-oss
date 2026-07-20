# GitHub Analyzer Development Makefile
.PHONY: help install install-dev test test-unit test-integration test-all lint format type-check clean build docs serve-docs

# Default target
help:
	@echo "GitHub Analyzer Development Commands"
	@echo "====================================="
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install      Install package in production mode"
	@echo "  make install-dev  Install package in development mode with dev dependencies"
	@echo "  make setup-env    Set up development environment from scratch"
	@echo ""
	@echo "Testing:"
	@echo "  make test         Run all tests"
	@echo "  make test-unit    Run unit tests only"
	@echo "  make test-integration  Run integration tests only"
	@echo "  make test-cov     Run tests with coverage report"
	@echo "  make test-api     Test API keys and connections"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint         Run linting checks (ruff)"
	@echo "  make format       Format code with ruff"
	@echo "  make type-check   Run type checking with mypy"
	@echo "  make quality      Run all quality checks (lint + type-check)"
	@echo ""
	@echo "Development:"
	@echo "  make clean        Clean build artifacts and cache"
	@echo "  make build        Build package for distribution"
	@echo "  make dev-check    Run all development checks (test + quality)"
	@echo ""
	@echo "Analysis:"
	@echo "  make analyze-repo URL=<github-url>  Analyze a specific repository"
	@echo "  make test-repos   Analyze all test repositories"
	@echo "  make benchmark    Run performance benchmarks"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs         Build documentation"
	@echo "  make serve-docs   Serve documentation locally"

# Setup & Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pip install pre-commit
	pre-commit install

setup-env:
	python -m venv venv
	@echo "Activate virtual environment with: source venv/bin/activate"
	@echo "Then run: make install-dev"

# Testing
test:
	pytest

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

test-cov:
	pytest --cov=src/github_analyzer --cov-report=html --cov-report=term

test-api:
	python scripts/test_api_keys.py

# Code Quality
lint:
	ruff check src/ tests/ scripts/

format:
	ruff format src/ tests/ scripts/

format-check:
	ruff format --check src/ tests/ scripts/

type-check:
	mypy src/github_analyzer/

quality: lint type-check

# Development workflow
dev-check: test quality
	@echo "✅ All development checks passed!"

# Cleaning
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Building
build: clean
	python -m build

# Analysis commands
analyze-repo:
	@if [ -z "$(URL)" ]; then echo "Usage: make analyze-repo URL=https://github.com/user/repo"; exit 1; fi
	python -m github_analyzer.cli.main $(URL)

test-repos:
	python scripts/test_all_repos.py

benchmark:
	python scripts/benchmark.py

# Documentation
docs:
	@echo "Documentation build not yet implemented"

serve-docs:
	@echo "Documentation server not yet implemented"

# Git helpers
commit-check: dev-check
	@echo "✅ Ready to commit!"

# Environment validation
check-env:
	@python -c "import sys; print(f'Python: {sys.version}')"
	@python -c "import github; print(f'PyGithub: {github.__version__}')"
	@python -c "import anthropic; print(f'Anthropic: {anthropic.__version__}')"
	@echo "Environment check complete"
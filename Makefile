.PHONY: help install install-dev test test-cov lint format clean build docs serve-docs

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install the package
	uv sync

install-dev: ## Install the package with development dependencies
	uv sync --extra dev --extra test --extra docs

test: ## Run tests
	pytest

test-cov: ## Run tests with coverage
	pytest --cov=cert_examtopics_quiz --cov-report=html --cov-report=term

lint: ## Run linting checks
	ruff check src tests
	mypy src

format: ## Format code
	ruff format src tests

check: ## Run all checks (lint + format check)
	ruff check src tests
	ruff format --check src tests
	mypy src

clean: ## Clean up build artifacts and cache
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

build: ## Build the package
	uv build

docs: ## Build documentation
	mkdocs build

serve-docs: ## Serve documentation locally
	mkdocs serve

run: ## Run the application
	python -m cert_examtopics_quiz.cli

install-pre-commit: ## Install pre-commit hooks
	pre-commit install

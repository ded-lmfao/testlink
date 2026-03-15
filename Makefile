# RevvLink Makefile
# Run make commands from the project root

.PHONY: help install dev-install checks format lint type test clean run pre-commit-setup

# Default target
help:
	@echo "RevvLink Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  install          - Install the package"
	@echo "  dev-install      - Install with dev dependencies"
	@echo "  checks           - Run all checks (format, lint, type, test)"
	@echo "  format           - Run ruff format"
	@echo "  lint             - Run ruff lint"
	@echo "  type             - Run pyright type checking"
	@echo "  test             - Run pytest"
	@echo "  clean            - Clean up cache files"
	@echo "  run              - Run the package"
	@echo "  pre-commit-setup - Install pre-commit hooks"
	@echo ""

# Installation
install:
	@echo "Installing RevvLink..."
	pip install -e .

dev-install:
	@echo "Installing RevvLink with dev dependencies..."
	pip install -e ".[dev]"

# All checks
checks: format lint type test
	@echo ""
	@echo "════════════════════════════════════════════════════════════"
	@echo "  ✓ All checks passed!"
	@echo "════════════════════════════════════════════════════════════"

# Individual checks
format:
	@echo "Running ruff format..."
	ruff format .

lint:
	@echo "Running ruff lint..."
	ruff check . --fix

type:
	@echo "Running pyright..."
	pyright revvlink/

test:
	@echo "Running pytest..."
	pytest tests/ -v --tb=short

# Quick test (quiet mode)
test-quick:
	@echo "Running quick tests..."
	pytest tests/ -q

# Clean up
clean:
	@echo "Cleaning up..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	rm -rf build/ dist/ *.egg-info/
	@echo "Clean complete!"

# Run the package
run:
	@echo "Running RevvLink..."
	python -m revvlink

# Setup pre-commit hooks
pre-commit-setup:
	@echo "Setting up pre-commit hooks..."
	@if [ -d ".git" ]; then \
		if [ ! -f ".git/hooks/pre-commit" ]; then \
			echo "Creating pre-commit hook..."; \
			mkdir -p .git/hooks; \
		fi; \
		chmod +x .git/hooks/pre-commit; \
		echo "Pre-commit hook installed!"; \
	else \
		echo "Error: Not a git repository"; \
	fi
	@echo ""
	@echo "To activate, run: pip install pre-commit && pre-commit install"

# CI pipeline (for GitHub Actions)
ci: lint type test
	@echo ""
	@echo "CI pipeline complete!"

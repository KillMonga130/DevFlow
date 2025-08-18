.PHONY: help install dev-install test lint format clean run

help:
	@echo "Available commands:"
	@echo "  install      Install production dependencies"
	@echo "  dev-install  Install development dependencies"
	@echo "  test         Run tests"
	@echo "  lint         Run linting"
	@echo "  format       Format code"
	@echo "  clean        Clean up build artifacts"
	@echo "  run          Run the development server"

install:
	pip install -r requirements.txt

dev-install:
	pip install -r requirements.txt
	pip install -e ".[dev,test]"

test:
	pytest

lint:
	flake8 src tests
	mypy src

format:
	black src tests

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run:
	uvicorn main:app --reload --host 0.0.0.0 --port 8000
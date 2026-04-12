# Makefile for MCP development and deployment commands

.PHONY: help install dev run stop clean docker-build docker-up docker-down migrate test lint

help:
	@echo "Master Control Program (MCP) - Makefile Commands"
	@echo ""
	@echo "Development:"
	@echo "  make install        - Install Python dependencies"
	@echo "  make dev            - Run in development mode with debug"
	@echo "  make test           - Run pytest test suite"
	@echo "  make lint           - Run linting (pylint, flake8)"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build   - Build Docker images"
	@echo "  make docker-up      - Start Docker containers"
	@echo "  make docker-down    - Stop Docker containers"
	@echo "  make docker-logs    - View Docker container logs"
	@echo ""
	@echo "Database:"
	@echo "  make migrate        - Run database migrations"
	@echo "  make db-init        - Initialize fresh database"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean          - Clean up temporary files"
	@echo "  make reset          - Full reset (delete data, logs, backups)"
	@echo ""

install:
	pip install --no-cache-dir -r requirements.txt
	@echo "✓ Dependencies installed"

dev:
	export MCP_DEBUG=true && python main.py

run:
	python main.py

stop:
	@kill $$(lsof -t -i :5000) 2>/dev/null || true
	@echo "✓ Stopped MCP services"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".DS_Store" -delete
	rm -rf .pytest_cache .coverage htmlcov
	@echo "✓ Cleaned up temporary files"

reset: clean
	rm -rf data logs backups
	mkdir -p data logs backups
	@echo "✓ Reset complete - recreated directories"

test:
	pytest tests/ -v --cov=. --cov-report=html
	@echo "✓ Tests complete - see htmlcov/index.html for coverage report"

lint:
	pylint **/*.py --disable=C0111,C0103,R0913 || true
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics || true

migrate:
	@echo "Running database migrations (Alembic)..."
	alembic upgrade head
	@echo "✓ Migrations applied"

db-init:
	@rm -f data/mcp.db
	@mkdir -p data logs backups
	python -c "from db.models import init_db; init_db('data/mcp.db'); print('✓ Database initialized')"

docker-build:
	docker-compose build --no-cache
	@echo "✓ Docker images built"

docker-up:
	docker-compose up -d
	@echo "✓ Docker containers started"
	@echo "   API: http://localhost:5000"
	@echo "   Dashboard: http://localhost"
	@echo "   Logs: docker-compose logs -f"

docker-down:
	docker-compose down
	@echo "✓ Docker containers stopped"

docker-logs:
	docker-compose logs -f

docker-restart: docker-down docker-up

docker-status:
	docker-compose ps

docker-shell:
	docker-compose exec mcp-api /bin/bash

.DEFAULT_GOAL := help

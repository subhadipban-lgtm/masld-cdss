.PHONY: help build up down logs test lint clean download-ref data

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build all Docker images
	docker compose build

up: ## Start all services
	docker compose up -d

down: ## Stop all services
	docker compose down

logs: ## Tail logs from all services
	docker compose logs -f

logs-web: ## Tail web service logs
	docker compose logs -f web

logs-worker: ## Tail worker service logs
	docker compose logs -f worker

restart: ## Restart all services
	docker compose restart

test: ## Run Python backend tests
	docker compose run --rm worker pytest backend/tests/ -v --tb=short

test-unit: ## Run unit tests only
	docker compose run --rm worker pytest backend/tests/ -v -m unit

test-integration: ## Run integration tests only
	docker compose run --rm worker pytest backend/tests/ -v -m integration

lint: ## Run Python linting
	docker compose run --rm worker ruff check backend/

format: ## Format Python code
	docker compose run --rm worker ruff format backend/

clean: ## Remove all containers, volumes, and images
	docker compose down -v --rmi all

download-ref: ## Download reference data (GENCODE, Salmon index, model weights)
	docker compose run --rm worker python scripts/download_reference_data.py

dev-frontend: ## Start Next.js frontend in development mode
	cd /home/z/my-project && bun run dev

shell: ## Open a shell in the worker container
	docker compose run --rm worker bash

db-migrate: ## Run database migrations
	docker compose run --rm web alembic upgrade head
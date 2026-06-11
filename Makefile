.PHONY: up down build restart logs migrate topics seed seed-data sanity clean help frontend-dev frontend-install

COMPOSE = docker compose
ENV_FILE = .env

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start all services (migrations run automatically on api_gateway startup)
	@cp -n $(ENV_FILE).example $(ENV_FILE) 2>/dev/null || true
	$(COMPOSE) up -d
	@echo "✓ Services started. API: http://localhost/api  UI: http://localhost  MinIO: http://localhost:9091"

down: ## Stop all services
	$(COMPOSE) down

build: ## Rebuild all images
	$(COMPOSE) build --no-cache

restart: ## Restart a specific service: make restart svc=api_gateway
	$(COMPOSE) restart $(svc)

logs: ## Tail logs for all services (or specific: make logs svc=api_gateway)
	$(COMPOSE) logs -f $(svc)

migrate: ## Run Alembic migrations manually (normally runs automatically on startup)
	$(COMPOSE) exec api_gateway alembic upgrade head

topics: ## Create Kafka topics (runs kafka-init container)
	$(COMPOSE) run --rm kafka-init

pull-models: ## Pull Ollama models (llama3, mistral, nomic-embed-text)
	$(COMPOSE) exec ollama bash /pull-models.sh

seed: ## Seed default users + compliance rules (admin@example.com / changeme)
	$(COMPOSE) exec api_gateway python seed.py

seed-data: ## Seed synthetic Forge SaaS documents (both scenarios, waits for processing)
	$(COMPOSE) run --rm \
		-v "$(PWD)/scripts:/scripts" \
		api_gateway \
		python /scripts/seed_data.py --base-url http://nginx:80 --wait $(args)

sanity: ## Run end-to-end sanity check (all 20 checks)
	$(COMPOSE) run --rm \
		-v "$(PWD)/scripts:/scripts" \
		api_gateway \
		python /scripts/sanity_check.py --base-url http://nginx:80 $(args)

ps: ## Show running containers
	$(COMPOSE) ps

clean: ## Remove all containers, volumes, and images
	$(COMPOSE) down -v --rmi local
	@echo "✓ All containers, volumes, and local images removed"

shell-api: ## Open shell in api_gateway container
	$(COMPOSE) exec api_gateway /bin/bash

shell-db: ## Open psql in postgres container
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-docstore} -d $${POSTGRES_DB:-docstore}

frontend-install: ## Install frontend dependencies with pnpm
	cd frontend && pnpm install

frontend-dev: ## Run frontend dev server locally (outside Docker)
	cd frontend && pnpm dev

test: ## Run integration tests
	$(COMPOSE) run --rm -e PYTHONPATH=/app api_gateway pytest /app/tests/ -v



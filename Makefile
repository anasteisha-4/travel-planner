.PHONY: up down build test lint fix dev logs clean migrate migration

# Docker
up:
	docker-compose up -d

down:
	docker-compose down -v

build:
	docker-compose build --no-cache

logs:
	docker-compose logs -f

# Development (local)
dev:
	docker-compose up -d postgres redis
	cd services/auth-service && uvicorn app.main:app --reload --port 8001

# Auth Service
test:
	docker-compose run --rm auth-service pytest tests/ -v
	docker-compose run --rm trip-service pytest tests/ -v

test-cov:
	docker-compose run --rm auth-service pytest --cov=app tests/
	docker-compose run --rm trip-service pytest --cov=app tests/

lint:
	cd services/auth-service && ruff check . --config ruff.toml

fix:
	cd services/auth-service && ruff check . --config ruff.toml --fix

# Install
install:
	cd services/auth-service && pip install -r requirements.txt

install-dev:
	pip install ruff pytest-cov

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true

# Database migrations
migrate:
	docker-compose run --rm auth-service alembic upgrade head
	docker-compose run --rm trip-service alembic upgrade head

migration:
	@read -p "Migration message: " msg; \
	docker-compose run --rm -v $$(pwd)/services/auth-service:/app auth-service alembic revision --autogenerate -m "$$msg"; \
	docker-compose run --rm -v $$(pwd)/services/trip-service:/app trip-service alembic revision --autogenerate -m "$$msg"

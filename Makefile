.PHONY: up down build test lint fix typecheck dev logs clean migrate migration seed-data fetch-poi-osm fetch-poi-otm compute-activities refresh-seasonality train-ranker train-budget build-features gen-ltr-pairs gen-budget-data dump-db dump-redis deploy-sync deploy-up deploy-logs deploy-ps

# Docker
up:
	docker-compose up -d

down:
	docker-compose down -v

build:
	docker-compose build --no-cache

up-front:
	docker compose build --no-cache frontend && docker compose up -d frontend

logs:
	docker-compose logs -f

# Development (local)
dev:
	docker-compose up -d postgres redis
	cd services/auth-service && uvicorn app.main:app --reload --port 8001

# Backend tests
test:
	docker-compose run --rm auth-service pytest tests/ -v
	docker-compose run --rm trip-service pytest tests/ -v
	docker-compose run --rm ml-service pytest tests/ -v
	docker-compose run --rm analytics-service pytest tests/ -v

test-cov:
	docker-compose run --rm auth-service pytest --cov=app tests/
	docker-compose run --rm trip-service pytest --cov=app tests/
	docker-compose run --rm ml-service pytest --cov=app tests/
	docker-compose run --rm analytics-service pytest --cov=app tests/

typecheck:
	cd services/auth-service && ../../.venv/bin/pyright
	cd services/trip-service && ../../.venv/bin/pyright
	cd services/ml-service && ../../.venv/bin/pyright
	cd services/analytics-service && ../../.venv/bin/pyright

lint: typecheck
	cd services/auth-service && ruff check . --config ruff.toml && cd ../trip-service && ruff check . --config ruff.toml && cd ../ml-service && ruff check . --config ruff.toml && cd ../analytics-service && ruff check . --config ruff.toml

fix:
	cd services/auth-service && ruff check . --config ruff.toml --fix && cd ../trip-service && ruff check . --config ruff.toml --fix && cd ../ml-service && ruff check . --config ruff.toml --fix && cd ../analytics-service && ruff check . --config ruff.toml --fix

# Install
install:
	cd services/auth-service && pip install -r requirements.txt

install-dev:
	pip install ruff pytest-cov pyright

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true

# Database migrations
migrate:
	docker-compose run --rm auth-service alembic upgrade head
	docker-compose run --rm trip-service alembic upgrade head
	docker-compose run --rm ml-service alembic upgrade head
	docker-compose run --rm analytics-service alembic upgrade head

migration:
	@read -p "Migration message: " msg; \
	docker-compose run --rm -v $$(pwd)/services/auth-service:/app auth-service alembic revision --autogenerate -m "$$msg"; \
	docker-compose run --rm -v $$(pwd)/services/trip-service:/app trip-service alembic revision --autogenerate -m "$$msg"

# Data ETL
seed-data:
	docker-compose run --rm data-service python -m etl.pipeline --seed

fetch-poi-osm:
	docker-compose run --rm data-service python -m etl.pipeline --jobs poi_osm $(if $(LIMIT),--limit $(LIMIT),)

fetch-poi-otm:
	docker-compose run --rm data-service python -m etl.pipeline --jobs poi_opentripmap $(if $(LIMIT),--limit $(LIMIT),)

compute-activities:
	docker-compose run --rm data-service python -m etl.pipeline --jobs activities,trajectories

refresh-seasonality:
	docker-compose run --rm data-service python -m etl.pipeline --jobs seasonality

# ML Training
gen-budget-data:
	docker-compose run --rm data-service python -m etl.scripts.generate_synthetic_data --table budgets

gen-ltr-pairs:
	docker-compose run --rm ml-service python scripts/generate_ltr_pairs.py --n-profiles 3000 --dests-per-query 150

train-ranker:
	docker-compose run --rm ml-service python scripts/train_ranker.py

train-budget:
	docker-compose run --rm ml-service python scripts/train_budget_model.py

build-features:
	docker-compose run --rm ml-service python -c "from sqlalchemy import create_engine; from sqlalchemy.orm import sessionmaker; from app.config import settings; from app.services.feature_matrix import build_destination_feature_matrix, save_feature_snapshot; engine = create_engine(settings.DATABASE_URL); db = sessionmaker(bind=engine)(); df = build_destination_feature_matrix(db); save_feature_snapshot(db, 3, len(df), 'manual'); print(f'Built {len(df)} destination features')"

# Deploy to Yandex Cloud VM
# Usage: make dump-db && make dump-redis  — run locally before deploy
# Then: make deploy-sync VM=ubuntu@<IP> && ssh into VM to restore data

dump-db:
	@echo "Dumping PostgreSQL (custom format, faster restore)..."
	docker-compose exec postgres pg_dump -U postgres -Fc travel_planner > travel_planner.dump
	@echo "Done: travel_planner.dump"

dump-redis:
	@echo "Saving Redis RDB..."
	docker-compose exec redis redis-cli SAVE
	docker-compose cp redis:/data/dump.rdb ./dump.rdb
	@echo "Done: dump.rdb"

deploy-sync:
	@test -n "$(VM)" || (echo "Usage: make deploy-sync VM=ubuntu@<IP>" && exit 1)
	rsync -avz --progress \
		--exclude='.git' \
		--exclude='node_modules' \
		--exclude='__pycache__' \
		--exclude='.pytest_cache' \
		--exclude='.ruff_cache' \
		--exclude='services/data-service/data' \
		--exclude='services/data-service/notebooks' \
		--exclude='.env.docker' \
		./ $(VM):~/travel-planner/
	@echo "Syncing data dumps..."
	scp travel_planner.dump dump.rdb $(VM):~/
	@echo "Sync complete. Next steps:"
	@echo "  1. ssh $(VM)"
	@echo "  2. cp ~/travel-planner/.env.prod.example ~/travel-planner/.env.prod && nano ~/travel-planner/.env.prod"
	@echo "  3. cd ~/travel-planner && make deploy-restore-db && make deploy-restore-redis"
	@echo "  4. make deploy-up"

deploy-up:
	docker compose -f docker-compose.prod.yml up -d

deploy-logs:
	docker compose -f docker-compose.prod.yml logs -f

deploy-ps:
	docker compose -f docker-compose.prod.yml ps

deploy-restore-db:
	@echo "Starting postgres..."
	docker compose -f docker-compose.prod.yml up -d postgres
	@echo "Waiting for postgres to be ready..."
	@until docker compose -f docker-compose.prod.yml exec postgres pg_isready -U postgres; do sleep 2; done
	@echo "Restoring dump (this may take 10-30 minutes for large DBs)..."
	docker compose -f docker-compose.prod.yml exec -T postgres \
		pg_restore -U postgres -d travel_planner --no-owner --role=postgres < ~/travel_planner.dump
	@echo "DB restored. Verifying..."
	docker compose -f docker-compose.prod.yml exec postgres \
		psql -U postgres -d travel_planner -c "SELECT count(*) AS destinations FROM destinations;"

deploy-restore-redis:
	@echo "Restoring Redis RDB..."
	docker compose -f docker-compose.prod.yml up -d redis
	docker compose -f docker-compose.prod.yml stop redis
	docker compose -f docker-compose.prod.yml cp ~/dump.rdb redis:/data/dump.rdb
	docker compose -f docker-compose.prod.yml start redis
	@echo "Redis restored."

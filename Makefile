.PHONY: dev server engine desktop db-migrate db-reset test lint build docker-up docker-down setup

# Development
dev: docker-up server engine desktop

server:
	cd packages/server && poetry run uvicorn src.main:app --reload --port 8000

engine:
	cd packages/local-engine && poetry run python -m src.server

desktop:
	cd packages/desktop && npm run electron:dev

# Database
db-migrate:
	cd packages/server && poetry run alembic upgrade head

db-reset:
	cd packages/server && poetry run alembic downgrade base && poetry run alembic upgrade head

# Testing
test:
	cd packages/server && poetry run pytest
	cd packages/local-engine && poetry run pytest

test-server:
	cd packages/server && poetry run pytest -v

test-engine:
	cd packages/local-engine && poetry run pytest -v

# Linting
lint:
	cd packages/server && poetry run ruff check src/
	cd packages/local-engine && poetry run ruff check src/
	cd packages/desktop && npm run lint

# Build
build:
	cd packages/desktop && npm run build

# Docker
docker-up:
	cd deploy && docker compose up -d

docker-down:
	cd deploy && docker compose down

# Setup
setup:
	@echo "Setting up IMEET.AI development environment..."
	cd deploy && docker compose up -d
	cd packages/server && poetry install
	cd packages/local-engine && poetry install
	cd packages/desktop && npm install
	@echo "Done! Run 'make dev' to start."

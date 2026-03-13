.PHONY: backend-install backend-format backend-lint backend-test frontend-install frontend-format frontend-lint frontend-test format lint test docker-up docker-down

# Backend commands
backend-install:
	cd backend && uv sync

backend-format:
	cd backend && uv run ruff format . && uv run ruff check . --fix

backend-lint:
	cd backend && uv run ruff check . && uv run mypy app

backend-test:
	cd backend && uv run pytest

# Frontend commands
frontend-install:
	cd frontend && npm install

frontend-format:
	cd frontend && npm run lint -- --fix

frontend-lint:
	cd frontend && npm run lint

frontend-test:
	echo "No tests configured for frontend yet"

# Combined commands
format: backend-format frontend-format
lint: backend-lint frontend-lint
test: backend-test frontend-test

# Docker commands
docker-up:
	docker compose up -d

docker-down:
	docker compose down

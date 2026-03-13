## Backend

FastAPI API, SQLAlchemy async data access, and Dramatiq worker runtime for
DealGraph Voice OS.

### Local setup

```bash
uv sync
uv run pytest -q
uv run ruff check .
uv run mypy app
```

### Run the API

```bash
uv run uvicorn app.main:app --reload
```

### Run the worker

```bash
uv run dramatiq app.workers.tasks
```

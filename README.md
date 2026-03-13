# DealGraph Voice OS

Enterprise Voice AI + Revenue Intelligence Platform.

## Quickstart

### Prerequisites
- Docker & Docker Compose
- Node.js >= 20
- Python 3.11+ & `uv`

### Running Locally

```bash
# Create a local env file first
# Windows PowerShell: Copy-Item .env.example .env
# macOS/Linux: cp .env.example .env

# Start all services
docker compose up -d

# View logs
docker compose logs -f
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs

## Local Development

```bash
make backend-install
make frontend-install
make lint
make test
```

## Live Bolna Validation

Use this only with real Bolna credentials, a public webhook URL, and a phone
number you control.

```bash
# Ensure these are configured in .env
# BOLNA_API_KEY
# BOLNA_AGENT_ID
# WEBHOOK_BASE_URL
# BOLNA_SMOKE_TEST_NUMBER
# BOLNA_CAPTURE_REAL_PAYLOADS=true

cd backend
uv run python scripts/live_bolna_smoke.py
```

When `BOLNA_CAPTURE_REAL_PAYLOADS=true`, the first real webhook and polling
payloads are captured into `BOLNA_CAPTURE_FIXTURES_DIR` for fixture-based tests.

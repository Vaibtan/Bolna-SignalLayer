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

# Signal Layer OS

Signal Layer OS is a self-hosted outbound Voice AI and revenue intelligence
platform for B2B deal teams.

It solves a common operating problem in enterprise sales: important stakeholder
conversations happen over calls, but the resulting knowledge is fragmented,
manual, and hard to turn into action. A rep or founder may know that a buyer is
stalled, that procurement is blocked, or that the economic buyer is still
missing, but that signal rarely becomes a structured, searchable system of
record.

This platform closes that gap by:

- placing outbound AI calls through Bolna
- ingesting webhook and polling updates reliably
- persisting transcripts and call events
- extracting structured deal intelligence with Gemini
- updating deal, stakeholder, and risk snapshots
- generating next-step recommendations and follow-up drafts
- storing semantic memory in Postgres with pgvector for retrieval

## What The Platform Contains

The current implementation includes the full core pipeline through Phase 12:

- authentication and org-scoped access control
- deal and stakeholder management
- outbound call initiation with throttling and cooldowns
- Bolna webhook ingestion with idempotency and polling fallback
- transcript persistence and timeline views
- extraction, evidence anchoring, and append-only snapshots
- deterministic deal risk scoring
- recommendation and draft generation
- semantic memory generation and retrieval with pgvector
- realtime delivery with WebSockets plus polling fallback
- audit logging, dead-letter handling, and transcript redaction/retention

## Architecture

This is intentionally built as a modular monolith that can run on a single
node, while keeping clean seams for later extraction.

### Runtime Components

- `web`: Next.js frontend on port `3000`
- `api`: FastAPI backend on port `8000`
- `worker`: Dramatiq worker for asynchronous pipelines
- `maintenance`: periodic scheduler for low-frequency maintenance jobs such as
  transcript retention sweeps
- `postgres`: Postgres with pgvector, exposed on host port `5433`
- `redis`: queue, rate limiting, idempotency, pub/sub, and dead-letter storage

### Core Flow

1. A user logs in and initiates a call for a stakeholder on a deal.
2. The backend validates org scope, applies Redis-backed throttling, persists a
   `CallSession`, and invokes the Bolna adapter.
3. Bolna sends webhook updates, and the system also polls execution status as a
   fallback.
4. Ingestion normalizes provider events, applies idempotency, appends
   `CallEvent` rows, and updates the `CallSession` projection.
5. Once a transcript is finalized, the worker runs extraction and stores an
   `ExtractionSnapshot` plus `EvidenceAnchor` rows.
6. The risk engine computes stakeholder, deal, and risk snapshots, and updates
   current projections on the deal and stakeholder records.
7. The recommendation pipeline generates action recommendations and follow-up
   drafts.
8. The memory pipeline creates semantic documents and embeds them into pgvector
   for search and retrieval.
9. Realtime hints are pushed over Redis pub/sub to WebSocket clients, while the
   frontend uses bounded polling as a resilience fallback.

### Data and Processing Design

- Postgres is the system of record.
- pgvector stores semantic embeddings inside the same database.
- Redis handles queueing, rate limiting, idempotency, dead-letter persistence,
  and realtime fan-out.
- Append-only artifacts are used where historical traceability matters:
  `CallEvent`, `ExtractionSnapshot`, `StakeholderSnapshot`, `DealSnapshot`,
  `RiskSnapshot`, `ActionRecommendation`, `FollowupDraft`, and `MemoryDocument`.
- Current read models are materialized on the main `Deal`, `Stakeholder`, and
  `CallSession` records for fast UI access.

## Manual Run Guide

This is the exact path to bring the full stack up locally with Docker and test
it against Postgres plus pgvector.

### 1. Prerequisites

- Docker Desktop with Compose
- A free local port set for `3000`, `8000`, `5433`, and `6379`
- For live calls only: Bolna credentials and a public webhook URL

### 2. Create `.env`

Copy the example file:

```powershell
Copy-Item .env.example .env
```

### 3. Choose Your Test Mode

For a local functional smoke test without real outbound calls, set this in
`.env`:

```env
BOLNA_MOCK_MODE=true
```

For real outbound call testing, set:

```env
BOLNA_MOCK_MODE=false
BOLNA_API_KEY=your_bolna_api_key
BOLNA_AGENT_ID=your_bolna_agent_id
WEBHOOK_BASE_URL=https://your-public-url
BOLNA_SMOKE_TEST_NUMBER=your_phone_number
BOLNA_CAPTURE_REAL_PAYLOADS=true
```

If you use a tunnel such as `ngrok`, `WEBHOOK_BASE_URL` should be the public URL
that reaches your local backend on port `8000`.

### 4. Build and Start the Stack

```powershell
docker compose up -d --build postgres redis api worker maintenance web
```

### 5. Run Database Migrations

The app does not auto-run migrations on startup. Apply them explicitly:

```powershell
docker compose run --rm api alembic upgrade head
```

This also creates the pgvector extension through the migration chain.

### 6. Seed Demo Data

```powershell
docker compose run --rm api python -m scripts.seed
```

Seeded credentials:

- email: `admin@signallayer.dev`
- password: `changeme123`

Seeded demo deal:

- `Acme Corp Enterprise License`

Seeded demo stakeholders:

- `Jane Chen` with phone
- `Marcus Rivera` with phone
- `Priya Sharma` without phone

### 7. Verify the Services

Open:

- frontend: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`
- liveness: `http://localhost:8000/api/health/live`
- readiness: `http://localhost:8000/api/health/ready`

Optional logs:

```powershell
docker compose logs -f api worker maintenance web
```

### 8. Manual Test Flow In The UI

1. Open `http://localhost:3000/login`.
2. Sign in with the seeded admin credentials.
3. Open the demo deal.
4. Start a call for `Jane Chen` or `Marcus Rivera`.
5. If you are in mock mode, the system should simulate the provider flow.
6. If you are in live mode, answer the call on the destination phone and let it
   complete.
7. Watch the call monitor page for status changes, transcript readiness, and
   post-call processing.
8. Return to the deal page and verify:
   - current risk score and risk level
   - deal coverage status
   - recommendations
   - follow-up drafts
9. Use the memory endpoints or later UI surfaces to verify semantic memory was
   generated.

### 9. Live Bolna Validation

For a direct provider smoke test outside the UI:

```powershell
docker compose run --rm api python scripts/live_bolna_smoke.py
```

You can also pass a specific phone number:

```powershell
docker compose run --rm api python scripts/live_bolna_smoke.py --phone +15551234567
```

When `BOLNA_CAPTURE_REAL_PAYLOADS=true`, the first real webhook and polling
payloads are captured into `BOLNA_CAPTURE_FIXTURES_DIR`.

### 10. Point Bolna Back To Your Local Backend

Your Bolna webhook target should be:

```text
{WEBHOOK_BASE_URL}/api/webhooks/bolna
```

If your tunnel URL changes, update `.env`, restart the affected services, and
update the webhook target in Bolna.

### 11. Helpful Operations

Stop the stack:

```powershell
docker compose down
```

Stop the stack and remove volumes:

```powershell
docker compose down -v
```

Re-run only migrations:

```powershell
docker compose run --rm api alembic upgrade head
```

Re-run only seed:

```powershell
docker compose run --rm api python -m scripts.seed
```

## Local Non-Docker Development

Backend:

```powershell
cd backend
uv sync
uv run pytest -q
uv run ruff check .
uv run mypy app
uv run uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
npm install
npm run lint
npm run build
npm run dev
```

## Current Status

The codebase is implemented through Phase 12 of the implementation plan. The
main remaining work is operational validation and demo hardening:

- real outbound-call validation with your Bolna setup
- capture of real webhook and polling fixtures
- final end-to-end demo hardening and recording

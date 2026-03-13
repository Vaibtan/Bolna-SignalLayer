# DealGraph Voice OS
## Implementation Plan

**Derived from:** [PRD.md](D:/SWE_DEV_NEW/Bolna-SignalLayer/PRD.md)
**Purpose:** Convert the approved PRD into an execution-ready, phase-based checklist.
**Execution model:** Single-node, self-hosted, modular monolith with a separate worker process on the same machine.

---

## 1. Implementation Strategy

Build this in vertical slices, not isolated subsystems.

Rules:

- Keep the app runnable after every phase.
- Prioritize the real demo path early: deal -> stakeholder -> call -> webhook -> transcript -> extraction -> risk -> recommendation.
- Build durable persistence before AI enrichment.
- Treat WebSockets as hints and durable read models as truth.
- Keep provider-specific logic behind adapters from day one.
- Do not block first recommendation on vector embedding completion.

Definition of done for each phase:

- Code is merged
- Migrations are applied
- Seed/demo flow still works
- Relevant tests for that phase pass
- Logging and error handling are good enough to debug the phase in isolation

---

## 2. Recommended Repository Layout

Create or align the codebase around this structure:

```text
backend/
  app/
    api/
    core/
    db/
    models/
    schemas/
    services/
      auth/
      deals/
      stakeholders/
      calls/
      bolna/
      transcripts/
      extraction/
      memory/
      risk/
      recommendations/
      realtime/
    workers/
    utils/
  migrations/
  tests/
  scripts/
frontend/
  src/
    app/
    components/
    features/
    hooks/
    lib/
    stores/
    types/
  tests/
ops/
  docker/
  caddy/
```

Recommendation:

- Backend queue library: `dramatiq` with Redis
- Backend validation: Pydantic v2
- Frontend data layer: TanStack Query
- Frontend transient UI state: Zustand

Queue runtime decision:

- Keep `dramatiq` for V1.
- Because the backend stack is async-first, Dramatiq actors should be thin synchronous wrappers that call async service entrypoints via `asyncio.run(...)`.
- Do not mix ad hoc async logic directly into actor bodies.
- If this boundary becomes painful during implementation spikes, reevaluate `taskiq` or `arq` before Phase 8 rather than mid-build.

---

## 3. Phase Checklist

## Phase 0: Repo Bootstrap and Tooling

Goal: establish the project skeleton and local developer workflow.

Checklist:

- [ ] Create backend and frontend workspace structure
- [ ] Add multi-stage Dockerfiles for `api`, `worker`, and `web`
- [ ] Add `docker-compose.yml` for `web`, `api`, `worker`, `postgres`, `redis`, and `proxy`
- [ ] Add `.env.example` from the PRD environment section
- [ ] Set up Python dependency management and JS package management
- [ ] Add formatting, linting, and test commands for both backend and frontend
- [ ] Add a root `README.md` with local startup instructions

Exit criteria:

- [ ] `docker compose up` boots all core services locally
- [ ] Frontend and backend health endpoints are reachable
- [ ] Team can start the app from a clean checkout

## Phase 1: Backend Foundation

Goal: create the backend runtime foundation before any business logic.

Checklist:

- [ ] Implement backend config loader from environment variables
- [ ] Configure FastAPI app, dependency injection, CORS, and health endpoints
- [ ] Configure SQLAlchemy async engine and session management
- [ ] Configure Alembic
- [ ] Configure Redis client and Dramatiq worker setup
- [ ] Configure Dramatiq middleware baseline, including `Retries`
- [ ] Implement the worker async boundary explicitly: Dramatiq actors remain sync wrappers and call async service entrypoints via `asyncio.run(...)`
- [ ] Define broker dead-letter retention behavior and exhausted-retry handling strategy
- [ ] Add an `on_retry_exhausted` path or equivalent failure sink for jobs that exceed retry policy
- [ ] Add structured logging with request IDs and job IDs
- [ ] Add error middleware and consistent API error shape

Exit criteria:

- [ ] Backend starts cleanly
- [ ] DB connection, Redis connection, and readiness checks work
- [ ] A sample background job can be enqueued and executed
- [ ] A sample failing job retries with backoff and lands in the dead-letter path after exhausting retries

## Phase 2: Auth and Organization Bootstrap

Goal: secure the app enough for V1 and create the seeded org/user path.

Checklist:

- [ ] Implement `Organization` and `User` models
- [ ] Add password hashing and login flow
- [ ] Add session or JWT auth for protected endpoints
- [ ] Implement `admin` and `operator` roles
- [ ] Add brute-force protection and auth rate limits
- [ ] Build frontend `/login` page and login form
- [ ] Create seed command for org + admin user

Exit criteria:

- [ ] User can log in and access protected routes
- [ ] Failed login throttling works
- [ ] Seeded admin user can access the app after fresh setup

## Phase 3: Core Domain Models and CRUD

Goal: make deals and stakeholders fully manageable before call flows.

Checklist:

- [ ] Implement models and migrations for `Deal`, `Stakeholder`, `CallSession`, and `CallEvent`
- [ ] Add service layer for deal CRUD
- [ ] Add service layer for stakeholder CRUD
- [ ] Implement `POST/GET/PATCH` deal endpoints
- [ ] Implement stakeholder endpoints
- [ ] Add frontend pages for deal list and deal workspace shell
- [ ] Add create deal and add stakeholder UI flows
- [ ] Add seed demo deal and stakeholders

Exit criteria:

- [ ] User can create a deal
- [ ] User can add/edit stakeholders
- [ ] Deal workspace renders seeded and user-created records

## Phase 4: Call Initiation and Bolna Adapter

Goal: support real outbound Bolna calls from the app.

Checklist:

- [ ] Implement Bolna adapter interface
- [ ] Implement call initiation API
- [ ] Create `CallSession(status=initiating)` before provider call
- [ ] Build `user_data` payload from current deal and stakeholder context
- [ ] Enforce context caps: `deal_context <= 3 sentences`, `open_questions <= 2`
- [ ] For `known_context`, use the latest `ExtractionSnapshot` summary if available; add memory-powered retrieval in Phase 11
- [ ] Persist provider request/response metadata
- [ ] Add rate limiting to call initiation endpoint
- [ ] Build frontend "Call with AI" modal
- [ ] Add UI states for initiation success, failure, and throttle response

Exit criteria:

- [ ] User can trigger a real outbound call to a configured phone number
- [ ] Duplicate or over-frequent call attempts are blocked safely
- [ ] Call session record is created even when provider initiation fails

## Phase 5: Webhook Ingestion, Idempotency, and Read Models

Goal: make provider events durable, replayable, and safe under duplicate delivery.

Checklist:

- [ ] Implement `POST /api/webhooks/bolna`
- [ ] Persist raw webhook payloads before heavy processing
- [ ] Add Redis-backed webhook idempotency key with 24-hour TTL
- [ ] Support fallback idempotency key generation from execution ID + status + payload hash
- [ ] Implement a shared `process_bolna_event(raw_payload, source=\"webhook\"|\"polling\")` ingestion entry point
- [ ] Normalize Bolna status values into internal event types
- [ ] Update `CallSession` projection from normalized events
- [ ] Add polling fallback for execution status and transcript retrieval
- [ ] Feed polling results through the same idempotency and normalization path as webhook payloads
- [ ] Capture at least one real webhook payload and one real polling response for fixture-based tests
- [ ] Add integration tests for duplicate terminal webhook delivery

Exit criteria:

- [ ] Duplicate webhooks do not create duplicate downstream work
- [ ] Call state transitions persist correctly
- [ ] Polling fallback can recover missed webhook state

## Phase 6: Realtime Delivery and Frontend Resilience

Goal: give the UI near-real-time updates without depending on WebSockets for correctness.

Checklist:

- [ ] Implement backend WebSocket endpoints for deals and calls
- [ ] Add Redis pub/sub bridge so `worker` and `api` can both trigger UI updates
- [ ] Emit lightweight "state changed" messages rather than full payloads
- [ ] Build call page and live status components
- [ ] Add active-state polling fallback in the frontend
- [ ] On WebSocket reconnect, invalidate active call and deal queries immediately
- [ ] Stop active-state polling once terminal call and extraction states are reached
- [ ] Add frontend tests for reconnect recovery and polling fallback

Exit criteria:

- [ ] UI updates during and after a call without full page reload
- [ ] UI recovers after browser sleep, tab restore, or network switch
- [ ] No page remains stuck in loading because a WebSocket update was missed

## Phase 7: Transcript Persistence and Call Timeline

Goal: make transcript and timeline artifacts durable and inspectable.

Checklist:

- [ ] Implement `TranscriptUtterance` storage model
- [ ] Add transcript normalization service
- [ ] Support transcript finalization from webhook or polling result
- [ ] Implement timeline query endpoint
- [ ] Render transcript drawer and call timeline in the frontend
- [ ] Ensure transcript storage succeeds even if later AI jobs fail

Exit criteria:

- [ ] Completed call shows transcript in UI
- [ ] Timeline shows call initiation, completion, and transcript receipt
- [ ] Raw call artifacts are inspectable in debug mode

## Phase 8: Extraction Pipeline and Evidence Anchors

Goal: convert transcript into schema-valid structured intelligence.

Checklist:

- [ ] Implement extraction schema in Pydantic
- [ ] Call `google-genai` using response-schema structured outputs
- [ ] Add `tenacity` retry loop for schema repair attempts
- [ ] Capture validation failures and retry up to configured budget
- [ ] Persist `ExtractionSnapshot`
- [ ] Persist `EvidenceAnchor`
- [ ] Add extraction processing state transitions
- [ ] Add unit tests for extraction normalization and validation-retry behavior

Exit criteria:

- [ ] Completed call produces a valid extraction artifact
- [ ] Critical extracted fields have evidence anchors
- [ ] Invalid model output does not crash the worker silently

## Phase 9: Risk Engine and Snapshot Updates

Goal: compute interpretable risk safely under concurrent call completions.

Checklist:

- [ ] Implement `StakeholderSnapshot`, `DealSnapshot`, and `RiskSnapshot`
- [ ] Implement deterministic risk scoring rules
- [ ] Add delta computation vs previous risk snapshot
- [ ] Acquire row-level lock on the `Deal` row before mutating projections and snapshots
- [ ] Ensure concurrent completions for the same deal do not corrupt the latest state
- [ ] Add unit tests for risk rules and concurrent update safety

Exit criteria:

- [ ] Risk updates after each processed call
- [ ] User can inspect major factors and deltas
- [ ] Concurrent worker runs do not produce inconsistent deal state

## Phase 10: Recommendations and Follow-up Drafts

Goal: generate actionable recommendations and operator-ready outputs.

Checklist:

- [ ] Implement recommendation input builder from extraction + risk + prior memory
- [ ] Implement `ActionRecommendation`
- [ ] Implement `FollowupDraft` including `crm_note`
- [ ] Ensure recommendation does not block on current-call embedding completion
- [ ] Implement accept, dismiss, and edit actions
- [ ] Render recommendation card and draft editor in the frontend
- [ ] Add tests for recommendation policy fallbacks

Exit criteria:

- [ ] After a call, the UI shows at least one recommendation
- [ ] Follow-up draft and CRM note are generated
- [ ] User can accept or dismiss recommendations

## Phase 11: Memory and pgvector

Goal: add semantic retrieval without slowing the first post-call result.

Checklist:

- [ ] Enable `pgvector`
- [ ] Implement `MemoryDocument`
- [ ] Generate call summary, objection summary, stakeholder summary, and action rationale documents
- [ ] Run embedding generation in a non-blocking branch
- [ ] Implement deal/stakeholder memory search endpoints
- [ ] Add debug UI for retrieved evidence and scores

Exit criteria:

- [ ] Memory documents are persisted and embedded
- [ ] Search returns ranked results
- [ ] Initial risk update and first recommendation are not blocked by embedding

## Phase 12: Rate Limit Hardening, Reliability, and Observability

Goal: make the system resilient enough for real calls and demo recording.

Checklist:

- [ ] Harden auth rate limits with Redis-backed counters, configurable lockouts, and observability
- [ ] Harden call initiation throttles with stakeholder cooldowns, admin overrides, and observability
- [ ] Add request size guard for webhook endpoint
- [ ] Add provider `429` backoff with jitter
- [ ] Bound worker concurrency
- [ ] Implement application-level dead-letter inspection, replay flow, and observability for exhausted jobs
- [ ] Add audit logging for manual edits
- [ ] Add retention and redaction controls for transcripts
- [ ] Add structured log fields for webhook ID, deal ID, call ID, and job ID

Exit criteria:

- [ ] Abuse controls work without breaking normal demo flow
- [ ] Worker backlog and failures are visible
- [ ] Failed jobs can be replayed safely

## Phase 13: Demo Hardening and Final Validation

Goal: make the recording and live demo reliable.

Checklist:

- [ ] Finalize Bolna agent in dashboard using the approved prompt and context limits
- [ ] Verify public webhook URL
- [ ] Run seed script for demo org, user, deal, and stakeholders
- [ ] Test real outbound calls to 2-3 personal numbers
- [ ] Capture one golden successful call fixture
- [ ] Capture one golden failure fixture (`no-answer` or `busy`)
- [ ] Verify the full operator flow on video: deal -> call -> transcript -> extraction -> risk -> recommendation -> follow-up
- [ ] Prepare fallback path using a pre-seeded completed call
- [ ] Validate rate limiting does not interfere with normal demo usage

Exit criteria:

- [ ] Screen recording can be completed end-to-end without manual DB intervention
- [ ] Real outbound call path works
- [ ] Mock/fallback path is available if provider reliability fails during recording

---

## 4. Cross-Cutting Checklist

Apply these in every phase:

- [ ] Add or update migrations with each schema change
- [ ] Add tests for the new behavior before moving to the next phase
- [ ] Update `.env.example` when config changes
- [ ] Keep seed data compatible with the current schema
- [ ] Keep raw provider payloads for debugging
- [ ] Preserve append-only event and snapshot history
- [ ] Do not hide failures behind silent retries

---

## 5. Recommended Execution Order for Demo Speed

If the goal is to reach a visible end-to-end demo as fast as possible, execute in this order:

1. Phase 0
2. Phase 1
3. Phase 2
4. Phase 3
5. Phase 4
6. Phase 5
7. Phase 6
8. Phase 7
9. Phase 8
10. Phase 9
11. Phase 10
12. Phase 13
13. Phase 11
14. Phase 12

Why this order:

- It gets the real call path working before polishing semantic memory.
- It keeps the first "wow moment" focused on post-call intelligence.
- It avoids spending early time on features that do not materially improve the assignment demo.

---

## 6. Final Notes

Do not start implementation by building the stakeholder graph, admin settings polish, or advanced analytics. Those are low leverage compared to:

- durable webhook ingestion
- transcript persistence
- extraction correctness
- risk clarity
- recommendation usefulness
- demo reliability

The first milestone worth showing to another person is:

- login works
- deal exists
- stakeholder exists
- outbound call starts
- webhook lands
- transcript is stored

The second milestone worth showing is:

- extraction is valid
- risk changes
- recommendation appears
- follow-up draft is generated

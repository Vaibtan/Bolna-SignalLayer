# Signal Layer OS
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

- [x] Create backend and frontend workspace structure
- [x] Add multi-stage Dockerfiles for `api`, `worker`, and `web`
- [x] Add `docker-compose.yml` for `web`, `api`, `worker`, `postgres`, `redis`, and `proxy`
- [x] Add `.env.example` from the PRD environment section
- [x] Set up Python dependency management and JS package management
- [x] Add formatting, linting, and test commands for both backend and frontend
- [x] Add a root `README.md` with local startup instructions

Exit criteria:

- [x] `docker compose up` boots all core services locally
- [x] Frontend and backend health endpoints are reachable
- [x] Team can start the app from a clean checkout

## Phase 1: Backend Foundation

Goal: create the backend runtime foundation before any business logic.

Checklist:

- [x] Implement backend config loader from environment variables
- [x] Configure FastAPI app, dependency injection, CORS, and health endpoints
- [x] Configure SQLAlchemy async engine and session management
- [x] Configure Alembic
- [x] Configure Redis client and Dramatiq worker setup
- [x] Configure Dramatiq middleware baseline, including `Retries`
- [x] Implement the worker async boundary explicitly: Dramatiq actors remain sync wrappers and call async service entrypoints via `asyncio.run(...)`
- [x] Define broker dead-letter retention behavior and exhausted-retry handling strategy
- [x] Add an `on_retry_exhausted` path or equivalent failure sink for jobs that exceed retry policy
- [x] Add structured logging with request IDs and job IDs
- [x] Add error middleware and consistent API error shape

Exit criteria:

- [x] Backend starts cleanly
- [x] DB connection, Redis connection, and readiness checks work
- [x] A sample background job can be enqueued and executed
- [x] A sample failing job retries with backoff and lands in the dead-letter path after exhausting retries

## Phase 2: Auth and Organization Bootstrap

Goal: secure the app enough for V1 and create the seeded org/user path.

Checklist:

- [x] Implement `Organization` and `User` models
- [x] Add password hashing and login flow
- [x] Add session or JWT auth for protected endpoints
- [x] Implement `admin` and `operator` roles
- [x] Add brute-force protection and auth rate limits
- [x] Build frontend `/login` page and login form
- [x] Create seed command for org + admin user

Exit criteria:

- [x] User can log in and access protected routes
- [x] Failed login throttling works
- [x] Seeded admin user can access the app after fresh setup

## Phase 3: Core Domain Models and CRUD

Goal: make deals and stakeholders fully manageable before call flows.

Checklist:

- [x] Implement models and migrations for `Deal`, `Stakeholder`, `CallSession`, and `CallEvent`
- [x] Add service layer for deal CRUD
- [x] Add service layer for stakeholder CRUD
- [x] Implement `POST/GET/PATCH` deal endpoints
- [x] Implement stakeholder endpoints
- [x] Add frontend pages for deal list and deal workspace shell
- [x] Add create deal and add stakeholder UI flows
- [x] Add seed demo deal and stakeholders

Exit criteria:

- [x] User can create a deal
- [x] User can add/edit stakeholders
- [x] Deal workspace renders seeded and user-created records

## Phase 4: Call Initiation and Bolna Adapter

Goal: support real outbound Bolna calls from the app.

Checklist:

- [x] Implement Bolna adapter interface
- [x] Implement call initiation API
- [x] Create `CallSession(status=initiating)` before provider call
- [x] Build `user_data` payload from current deal and stakeholder context
- [x] Enforce context caps: `deal_context <= 3 sentences`, `open_questions <= 2`
- [x] For `known_context`, use the latest `ExtractionSnapshot` summary if available; add memory-powered retrieval in Phase 11
- [x] Persist provider request/response metadata
- [x] Add rate limiting to call initiation endpoint
- [x] Build frontend "Call with AI" modal
- [x] Add UI states for initiation success, failure, and throttle response

Exit criteria:

- [ ] User can trigger a real outbound call to a configured phone number
- [x] Duplicate or over-frequent call attempts are blocked safely
- [x] Call session record is created even when provider initiation fails

## Phase 5: Webhook Ingestion, Idempotency, and Read Models

Goal: make provider events durable, replayable, and safe under duplicate delivery.

Checklist:

- [x] Implement `POST /api/webhooks/bolna`
- [x] Persist raw webhook payloads before heavy processing
- [x] Add Redis-backed webhook idempotency key with 24-hour TTL
- [x] Support fallback idempotency key generation from execution ID + status + payload hash
- [x] Implement a shared `process_bolna_event(raw_payload, source=\"webhook\"|\"polling\")` ingestion entry point
- [x] Normalize Bolna status values into internal event types
- [x] Update `CallSession` projection from normalized events
- [x] Add polling fallback for execution status and transcript retrieval
- [x] Feed polling results through the same idempotency and normalization path as webhook payloads
- [ ] Capture at least one real webhook payload and one real polling response for fixture-based tests
- [x] Add integration tests for duplicate terminal webhook delivery

Exit criteria:

- [x] Duplicate webhooks do not create duplicate downstream work
- [x] Call state transitions persist correctly
- [x] Polling fallback can recover missed webhook state

## Phase 6: Realtime Delivery and Frontend Resilience

Goal: give the UI near-real-time updates without depending on WebSockets for correctness.

Checklist:

- [x] Implement backend WebSocket endpoints for deals and calls
- [x] Add Redis pub/sub bridge so `worker` and `api` can both trigger UI updates
- [x] Emit lightweight "state changed" messages rather than full payloads
- [x] Build call page and live status components
- [x] Add active-state polling fallback in the frontend
- [x] On WebSocket reconnect, invalidate active call and deal queries immediately
- [x] Stop active-state polling once terminal call and extraction states are reached
- [x] Add frontend tests for reconnect recovery and polling fallback

Exit criteria:

- [x] UI updates during and after a call without full page reload
- [x] UI recovers after browser sleep, tab restore, or network switch
- [x] No page remains stuck in loading because a WebSocket update was missed

## Phase 7: Transcript Persistence and Call Timeline

Goal: make transcript and timeline artifacts durable and inspectable.

Checklist:

- [x] Implement `TranscriptUtterance` storage model
- [x] Add transcript normalization service
- [x] Support transcript finalization from webhook or polling result
- [x] Implement timeline query endpoint
- [x] Render transcript drawer and call timeline in the frontend
- [x] Ensure transcript storage succeeds even if later AI jobs fail

Exit criteria:

- [x] Completed call shows transcript in UI
- [x] Timeline shows call initiation, completion, and transcript receipt
- [x] Raw call artifacts are inspectable in debug mode

## Phase 8: Extraction Pipeline and Evidence Anchors

Goal: convert transcript into schema-valid structured intelligence.

Checklist:

- [x] Implement extraction schema in Pydantic
- [x] Call `google-genai` using response-schema structured outputs
- [x] Add `tenacity` retry loop for schema repair attempts
- [x] Capture validation failures and retry up to configured budget
- [x] Persist `ExtractionSnapshot`
- [x] Persist `EvidenceAnchor`
- [x] Add extraction processing state transitions
- [x] Add unit tests for extraction normalization and validation-retry behavior

Exit criteria:

- [x] Completed call produces a valid extraction artifact
- [x] Critical extracted fields have evidence anchors
- [x] Invalid model output does not crash the worker silently

## Phase 9: Risk Engine and Snapshot Updates

Goal: compute interpretable risk safely under concurrent call completions.

Checklist:

- [x] Implement `StakeholderSnapshot`, `DealSnapshot`, and `RiskSnapshot`
- [x] Implement deterministic risk scoring rules
- [x] Add delta computation vs previous risk snapshot
- [x] Acquire row-level lock on the `Deal` row before mutating projections and snapshots
- [x] Ensure concurrent completions for the same deal do not corrupt the latest state
- [x] Add unit tests for risk rules and concurrent update safety

Exit criteria:

- [x] Risk updates after each processed call
- [x] User can inspect major factors and deltas
- [x] Concurrent worker runs do not produce inconsistent deal state

## Phase 10: Recommendations and Follow-up Drafts

Goal: generate actionable recommendations and operator-ready outputs.

Checklist:

- [x] Implement recommendation input builder from extraction + risk + prior memory
- [x] Implement `ActionRecommendation`
- [x] Implement `FollowupDraft` including `crm_note`
- [x] Ensure recommendation does not block on current-call embedding completion
- [x] Implement accept, dismiss, and edit actions
- [x] Render recommendation card and draft editor in the frontend
- [x] Add tests for recommendation policy fallbacks

Exit criteria:

- [x] After a call, the UI shows at least one recommendation
- [x] Follow-up draft and CRM note are generated
- [x] User can accept or dismiss recommendations

## Phase 11: Memory and pgvector

Goal: add semantic retrieval without slowing the first post-call result.

Checklist:

- [x] Enable `pgvector`
- [x] Implement `MemoryDocument`
- [x] Generate call summary, objection summary, stakeholder summary, and action rationale documents
- [x] Run embedding generation in a non-blocking branch
- [x] Implement deal/stakeholder memory search endpoints
- [ ] Add debug UI for retrieved evidence and scores

Exit criteria:

- [x] Memory documents are persisted and embedded
- [x] Search returns ranked results
- [x] Initial risk update and first recommendation are not blocked by embedding

## Phase 12: Rate Limit Hardening, Reliability, and Observability

Goal: make the system resilient enough for real calls and demo recording.

Checklist:

- [x] Harden auth rate limits with Redis-backed counters, configurable lockouts, and observability
- [x] Harden call initiation throttles with stakeholder cooldowns, admin overrides, and observability
- [x] Add request size guard for webhook endpoint
- [x] Add provider `429` backoff with jitter
- [x] Bound worker concurrency
- [x] Implement application-level dead-letter inspection, replay flow, and observability for exhausted jobs
- [x] Add audit logging for manual edits
- [x] Add retention and redaction controls for transcripts
- [x] Add structured log fields for webhook ID, deal ID, call ID, and job ID

Exit criteria:

- [x] Abuse controls work without breaking normal demo flow
- [x] Worker backlog and failures are visible
- [x] Failed jobs can be replayed safely

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

- [x] Add or update migrations with each schema change
- [x] Add tests for the new behavior before moving to the next phase
- [x] Update `.env.example` when config changes
- [x] Keep seed data compatible with the current schema
- [x] Keep raw provider payloads for debugging
- [x] Preserve append-only event and snapshot history
- [x] Do not hide failures behind silent retries

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

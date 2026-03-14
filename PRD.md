# Signal Layer OS
## Product Requirements Document (PRD)

**Version:** v1.2
**Status:** Revised with implementation-ready specifications
**Owner:** Vaibhav Tanwar
**Product type:** Enterprise Voice AI + Revenue Intelligence Platform
**Preferred stack:** FastAPI backend, Next.js frontend
**Deployment target:** Self-hosted, single-node, multi-stage Docker builds
**Voice provider constraint:** Bolna for all voice AI capabilities

---

## 1. Executive Summary

Signal Layer OS is a voice-native revenue intelligence system for complex B2B sales. It uses autonomous voice interactions to engage stakeholders, captures structured signals from conversations, maintains evolving deal memory across calls, detects risk, and recommends the next best action to move a deal forward.

The product thesis is that the lasting value is not the phone call itself. The lasting value is the structured, inspectable, evidence-linked deal memory created from those calls.

For V1, the system will support one high-value workflow:

1. A user opens a deal workspace.
2. The user selects a stakeholder and triggers an outbound Bolna voice call.
3. Live call state and transcript events stream into the UI.
4. After the call, the backend extracts structured signals and updates deal memory.
5. The system recomputes risk, identifies what changed, and recommends the next best action.

This PRD intentionally targets a senior-level production-style implementation while remaining realistic for a single-node self-hosted deployment and an assignment-grade end-to-end demo.

---

## 2. Assignment Alignment

The Bolna assignment asks for:

- A real enterprise use case
- A Bolna voice AI agent
- A web app around the agent
- An end-to-end flow from user to backend output
- A demo recording and repo

This PRD exceeds the minimum assignment by treating the app as a production-shaped system, not a thin demo wrapper. The design remains intentionally constrained in ways that preserve execution speed:

- V1 is a modular monolith, not a microservice fleet.
- Deployment is single-node, not distributed infrastructure.
- Postgres with `pgvector` is the only primary database.
- Redis is used for queues and pub/sub.
- Bolna is the only voice provider in V1.
- The app is single-org in implementation, while retaining clean boundaries for later multi-tenant expansion.

---

## 3. Product Thesis and Positioning

### 3.1 Product thesis

Revenue teams lose deals because account knowledge is fragmented across calls, notes, CRM records, and rep memory. Voice AI can collect information, but collection alone is not enough. The system must convert conversations into evolving deal state that can be audited, queried, and acted on.

### 3.2 What the product is

- A voice-enabled deal intelligence platform
- A structured memory layer for multi-stakeholder sales cycles
- A risk detection and action recommendation engine
- A workspace for operators to inspect evidence and act quickly

### 3.3 What the product is not

- Not just a cold-calling bot
- Not just a meeting booking assistant
- Not just a transcript summarizer
- Not just a CRM wrapper
- Not a full contact center platform

### 3.4 Product wedge

The wedge is multi-stakeholder deal memory and interpretable deal risk built from real voice interactions.

---

## 4. Problem Statement

In B2B sales, critical account knowledge is fragmented and decays quickly.

Common failure modes:

- Teams do not know who the real decision-maker is.
- Objections repeat across conversations but are never consolidated.
- Deals become single-threaded around one champion.
- Procurement, legal, and security blockers are discovered too late.
- Reps complete calls without a concrete next step.
- CRM records are stale or incomplete.
- Managers cannot explain why a deal is at risk without reading raw transcripts.

Existing AI SDR products often optimize for top-of-funnel activity. They do not deeply model the state of a complex deal across multiple stakeholders and multiple interactions.

Signal Layer OS addresses this by making every important conversational signal structured, versioned, evidence-linked, and reusable.

---

## 5. Users and Jobs To Be Done

### 5.1 Primary persona: Account Executive

Needs:

- Understand account status quickly
- Recover context across stakeholders
- Identify blockers and champions
- Know who to engage next and why

JTBD:

"When I am working a deal with multiple stakeholders, help me know what changed, what matters, and what I should do next."

### 5.2 Secondary persona: Sales Manager

Needs:

- See which deals are at risk
- Understand why they are at risk
- Coach based on conversational evidence
- Monitor whether an account is properly multi-threaded

JTBD:

"When a deal is slipping, show me the reasons with evidence and suggest the best intervention."

### 5.3 Tertiary persona: RevOps

Needs:

- Standardized qualification data
- Better CRM hygiene
- Structured deal metadata
- Repeatable operational workflows

JTBD:

"When calls happen, convert them into structured and reusable revenue signals without manual cleanup."

### 5.4 Operational persona: Voice workflow owner

Needs:

- Trigger stakeholder calls
- Track outcomes
- Trust that call output flows into downstream intelligence

---

## 6. Goals

### 6.1 Product goals

- Capture structured intelligence from voice calls
- Build evolving deal memory across conversations
- Detect risk and missing information automatically
- Recommend the next best stakeholder action
- Surface intelligence in a clean operator dashboard

### 6.2 Engineering goals

- Build a modular monolith with clean internal boundaries
- Use FastAPI for APIs, webhooks, WebSockets, and orchestration
- Use Next.js App Router for the operator UI
- Keep all AI outputs inspectable, versioned, and replayable
- Support single-node self-hosting with Docker Compose
- Preserve architecture seams for later multi-tenant expansion

### 6.3 Demo goals

- Show user -> web app -> Bolna voice agent -> backend logic -> UI output
- Demonstrate a real outbound call to a real phone number
- Show live call status and at least partial transcript updates
- Show post-call extraction, risk update, and next-best action

---

## 7. Success Metrics

### 7.1 Product metrics

- Percentage of completed calls that produce a valid structured extraction
- Percentage of deals with at least one identified next step
- Percentage of deals with at least two mapped stakeholders
- Percentage of recommendations accepted or edited by users
- Median time from call completion to recommendation generation

### 7.2 Demo metrics

- User can initiate a Bolna call from the UI
- At least one live event appears in the UI during a real call
- Transcript is stored and visible after the call
- Risk score updates after the call
- Next-best action is generated and explained
- Full flow can be shown in a screen recording without manual DB edits

### 7.3 AI quality metrics

- Schema-valid extraction rate
- Evidence coverage rate for critical fields
- Percentage of required fields returned as `unknown` instead of hallucinated
- Recommendation grounding rate against current deal state

---

## 8. Scope

### 8.1 V1 scope

V1 focuses on one workflow: stakeholder recovery and deal risk update.

Workflow:

- A deal exists with two to four stakeholders
- The system identifies missing information or elevated risk
- The user triggers a voice call to one stakeholder
- The call is processed and intelligence is extracted
- The system updates deal state and recommends the next step

Included in V1:

- Deal workspace
- Stakeholder management
- Outbound Bolna voice call initiation
- Live call state and transcript streaming
- Structured extraction from transcript
- Deal memory with `pgvector`
- Risk scoring with evidence-linked factors
- Next-best action generation
- Follow-up draft generation
- Timeline and audit trail
- Basic auth for a single org
- Single-node self-hosted deployment

### 8.2 Explicit non-goals for V1

- Full CRM sync with Salesforce or HubSpot
- Enterprise SSO, SCIM, or advanced RBAC
- Multi-tenant billing
- Predictive revenue forecasting
- Multi-node orchestration
- Provider-agnostic telephony abstraction
- Large analytics warehouse integrations
- Automatic email sending

### 8.3 Stretch features after V1

- Stakeholder graph visualization
- CRM sync adapters
- Slack and email notifications
- Campaign orchestration across multiple calls
- Manager coaching insights
- Outcome analytics dashboard
- Multi-tenant org isolation

### 8.4 Clarification on CRM note output

V1 will generate a "CRM note" as plain text that a user could paste into a CRM such as Salesforce or HubSpot. It will not write back into a CRM automatically. This keeps V1 small while preserving a useful downstream artifact.

---

## 9. Product Principles

1. Voice is an input channel, not the full product.
2. Every important signal must become structured.
3. AI outputs must be editable, inspectable, and traceable to evidence.
4. The user interface must support action, not just observation.
5. Internal state changes must be replayable from persisted events and artifacts.
6. V1 should feel production-shaped even if some enterprise features are deferred.

---

## 10. Core User Journeys

### 10.1 Happy path

1. User opens the deal workspace.
2. User reviews current risk, stakeholders, and open questions.
3. User chooses a stakeholder and a call objective.
4. Backend composes a Bolna call context package from deal memory.
5. Bolna places the outbound call.
6. Provider events flow to the backend webhook.
7. Backend stores raw events and normalized call state.
8. Frontend receives live updates over WebSocket.
9. Transcript segments are stored incrementally.
10. When the call ends, the extraction pipeline runs.
11. Memory documents are embedded into `pgvector`.
12. Risk is recomputed from current snapshots and extracted signals.
13. Recommendation engine generates the next best action and follow-up drafts.
14. UI updates the risk panel, timeline, stakeholder state, and action center.

### 10.2 Important alternate paths

- Call not answered
- Call answered but stakeholder refuses discussion
- Call drops before objective completion
- Stakeholder asks for email only
- Stakeholder names a new decision-maker
- Stakeholder raises a security or procurement blocker
- Transcript arrives partially or out of order
- Extraction fails but transcript storage succeeds
- Vector retrieval fails but risk and recommendations still proceed

---

## 11. Architecture Strategy

### 11.1 Chosen architecture

V1 will be a modular monolith.

Why this is the correct choice:

- It is the fastest way to produce a production-quality system under assignment constraints.
- It avoids premature distributed systems complexity.
- It still supports clean boundaries between domains such as calls, extraction, memory, and risk.
- It is easy to deploy on a single node.
- It can evolve into services later if load or team size justifies the split.

### 11.2 Internal architecture principles

- Route handlers stay thin.
- Business logic lives in service modules.
- Provider integrations live behind adapters.
- Append-only events and snapshots are stored for replayability.
- Read models are materialized into deal and stakeholder state for fast UI reads.
- AI outputs are versioned with schema version, prompt version, and model metadata.

### 11.3 Key technical decisions

- Postgres is the primary database.
- `pgvector` is the vector store.
- Redis is used for queueing, retries, and pub/sub.
- Bolna is the voice provider.
- FastAPI owns APIs, webhooks, WebSockets, and orchestration.
- Post-call processing runs through a durable Redis-backed job queue from day one. The API only enqueues work; a separate worker process executes extraction, embedding, risk, and recommendation jobs. The processing pipeline is implemented as callable service modules so scaling the worker is a deployment change, not a code rewrite.

### 11.4 Tech stack versions

**Backend:** Python 3.11+, FastAPI 0.115+, SQLAlchemy 2.x, Alembic, Pydantic v2, `google-genai` SDK, asyncpg, redis-py, uvicorn
**Frontend:** Next.js 14+ (App Router), TypeScript, Tailwind CSS, shadcn/ui, TanStack Query, Zustand (or React Context for lighter state)
**Infrastructure:** Docker, Docker Compose, PostgreSQL 16 + pgvector, Redis 7, Caddy (reverse proxy with automatic TLS)

---

## 12. Deployment Topology

### 12.1 Single-node deployment

The initial deployment runs on one machine using Docker Compose.

Services:

- `web`: Next.js frontend
- `api`: FastAPI application
- `worker`: background job processor for post-call intelligence
- `postgres`: Postgres with `pgvector`
- `redis`: queue and pub/sub
- `proxy`: Caddy reverse proxy with automatic TLS

Note: V1 still remains single-node. The worker is a separate process on the same machine, not a distributed systems jump.

### 12.2 Operational notes

- All services use named Docker volumes for persistence where needed.
- Postgres data is persisted locally.
- Redis can be ephemeral for V1, but persistence is preferred.
- Reverse proxy exposes public HTTPS endpoints for the app and Bolna webhooks.
- Local development can use a tunnel if required for webhook delivery.

### 12.3 Multi-stage Docker requirement

Each deployable service must support multi-stage Docker builds to keep images small and reproducible.

Required images:

- Frontend image
- API image
- Worker image

### 12.4 Backups and recovery

- Daily Postgres backups are required even in demo environments where practical.
- Raw call events and normalized artifacts must be restorable from DB backups.
- Redis does not need to be the source of truth; all durable state must live in Postgres.

---

## 13. External Integrations

### 13.1 Bolna integration boundary

Bolna is responsible for:

- Outbound voice call execution
- Execution lifecycle status updates
- Transcript delivery for completed executions
- Partial transcript delivery only if supported by the chosen Bolna configuration
- Optional recording metadata if available

Our system is responsible for:

- Initiating calls through a Bolna adapter
- Persisting raw webhook payloads
- Normalizing provider events into internal event types
- Building call context and prompts
- Running downstream extraction, risk, and recommendation logic

#### 13.1.1 Bolna Agent ID lifecycle

The Bolna agent (`BOLNA_AGENT_ID`) is created once on the Bolna dashboard and reused for all outbound calls. Per-call customization (deal context, stakeholder info, call objective) is passed via the `user_data` field in the call initiation API request. The agent's base system prompt on Bolna references these variables using template placeholders so that each call is contextually unique without requiring multiple agents.

#### 13.1.2 Bolna API contract

**Outbound call initiation:**

```
POST https://api.bolna.ai/call
Headers:
  Authorization: Bearer <BOLNA_API_KEY>
Content-Type: application/json
Body:
{
  "agent_id": "<BOLNA_AGENT_ID>",
  "recipient_phone_number": "+1XXXXXXXXXX",
  "user_data": {
    "stakeholder_name": "Rahul Mehta",
    "stakeholder_title": "VP Operations",
    "company_name": "Acme Corp",
    "deal_context": "...",
    "call_objective": "discovery_qualification",
    "open_questions": ["..."]
  }
}
```

The `user_data` object is injected into the agent's system prompt at call time, enabling dynamic context without modifying the agent configuration.

**Webhook payload:**

Bolna delivers execution data to our configured webhook URL. For V1, the canonical assumption is completion-oriented delivery plus polling fallback, not guaranteed word-by-word streaming. The webhook payload should be treated as execution-style data and validated against a captured real payload before the parser is finalized.

Key fields to normalize:

- `id` or execution identifier — maps to `provider_call_id`
- `status` — provider status such as `queued`, `ringing`, `in-progress`, `completed`, `busy`, `no-answer`, `canceled`, `failed`, `stopped`, or `error`
- `transcript` — canonical post-call transcript content; treat it as provider-owned transcript text unless captured payloads prove segment-level delivery
- `recording_url` or equivalent nested metadata if recording is enabled
- `duration` or equivalent duration metadata
- `created_at` and `updated_at` timestamps when available

**Webhook status mapping:**

| Bolna Status | Internal Event Type | Source |
|---|---|---|
| — | `call.initiated` | Synthetic (our system, on call creation) |
| `queued` | `call.queued` | Bolna webhook or polling |
| `ringing` | `call.ringing` | Bolna webhook or polling |
| `in-progress` | `call.started` | Bolna webhook or polling |
| `completed` | `call.completed` | Bolna webhook |
| `busy` | `call.busy` | Bolna webhook or polling |
| `no-answer` | `call.no_answer` | Bolna webhook or polling |
| `canceled` | `call.canceled` | Bolna webhook or polling |
| `failed`, `stopped`, `error` | `call.failed` | Bolna webhook or polling |
| terminal payload with transcript text | `transcript.final` | Bolna webhook or polling |
| — | `extraction.completed` | Synthetic (our system) |
| — | `risk.updated` | Synthetic (our system) |
| — | `recommendation.created` | Synthetic (our system) |

Notes:

- `call.initiated` is created when our API creates the `CallSession`; it does not come from a provider status.
- `transcript.partial` remains a forward-compatible internal event type, but V1 does not require a handler for it unless captured Bolna payloads prove partial transcript delivery is available.

**Get Execution API (polling fallback):**

```
GET https://api.bolna.ai/executions/<execution_id>
Headers:
  Authorization: Bearer <BOLNA_API_KEY>
```

Use this as a fallback if webhook delivery is delayed or missed. Poll with exponential backoff.

Polling strategy for V1:

- Poll every 5 seconds after call initiation until a terminal provider status is observed or a completion webhook is received
- Stop polling immediately once a terminal state is persisted
- Prefer webhook payloads when both polling and webhook data are present, but retain both raw payloads for auditability

Webhook idempotency for V1:

- Each incoming webhook must be checked against a Redis idempotency key with a 24-hour TTL
- Preferred key format: `signal_layer:webhook:bolna:{provider_event_id}`
- If Bolna does not provide a stable event ID, derive the key from execution ID, terminal status, and a payload hash
- Duplicate webhook deliveries must be acknowledged safely without re-running downstream processing

**Webhook network controls:** Do not hardcode a single provider IP in the PRD. If Bolna provides fixed egress IPs for your account, expose them via configuration. Otherwise rely on secret-bearing webhook validation, idempotency keys, and standard ingress protection.

**Authentication:** Bearer token obtained from Bolna dashboard → Developers tab.

### 13.2 Text model and embeddings boundary

V1 uses **Google Gemini** as the primary LLM provider for all backend AI pipelines (extraction, risk narrative, recommendation generation).

**Primary LLM:** `gemini-2.5-flash` for extraction and risk scoring. `gemini-2.5-pro` for recommendation generation where higher quality justifies latency.

**Embedding model:** `gemini-embedding-001` for pgvector embeddings.

**SDK:** `google-genai` Python SDK.

**Rationale:** These are the current supported Gemini-family defaults and avoid baking deprecated model identifiers into the implementation plan. All model names are configuration-driven so they can be updated without code changes.

Constraints:

- Prompt templates must be versioned.
- Structured outputs must be schema-validated.
- Embedding generation must write into `pgvector`.
- Extraction must use SDK-level structured output enforcement with the Pydantic schema passed as the response schema, rather than relying on free-form text plus manual JSON parsing.

### 13.3 Bolna Agent Design

#### 13.3.1 Agent specification

- **Agent name:** Signal Layer Discovery Agent
- **LLM on Bolna:** GPT-4o (via Bolna's platform LLM selection)
- **TTS voice:** ElevenLabs, professional voice (e.g., "Rachel" or equivalent business-appropriate voice)
- **STT:** Bolna default (Deepgram)
- **Language:** English

#### 13.3.2 Welcome message template

```
Hello {stakeholder_name}, this is the Signal Layer assistant calling on behalf of the {company_name} engagement team. I'm reaching out regarding your {deal_context_brief}. Do you have a few minutes to discuss?
```

Variables `{stakeholder_name}`, `{company_name}`, and `{deal_context_brief}` are populated from `user_data` at call time.

#### 13.3.3 Agent system prompt

```
You are a professional B2B sales intelligence analyst conducting a structured phone conversation. You work for the Signal Layer OS platform.

## Your Identity
- You are polite, concise, and professional.
- You do not pretend to be a human. If asked, you identify as an AI assistant.
- You speak in clear, short sentences appropriate for a phone call.

## Context (injected per call)
- Stakeholder: {stakeholder_name}, {stakeholder_title} at {company_name}
- Deal: {deal_context}
- Call Objective: {call_objective}
- Open Questions: {open_questions}
- Known Information: {known_context}

## Call Objective Instructions

### If call_objective is "discovery_qualification":
- Understand the stakeholder's role in the buying process
- Identify who makes the final purchasing decision
- Explore budget availability and timeline expectations
- Uncover any known blockers (security, legal, procurement)
- Identify other stakeholders involved in the process

### If call_objective is "timeline_procurement_validation":
- Confirm or update the expected decision timeline
- Understand the procurement process and required steps
- Identify any approval gates or review cycles
- Ask about budget cycle alignment
- Clarify who needs to sign off

### If call_objective is "blocker_clarification":
- Understand the specific nature of the blocker (security, legal, compliance, technical)
- Identify who owns the resolution of this blocker
- Ask what documentation or evidence would help resolve it
- Explore timeline for blocker resolution
- Determine if there are workarounds or interim steps

## Guardrails
- NEVER hallucinate or fabricate facts about the company, product, or prior conversations.
- NEVER make commitments, promises about pricing, or contractual statements.
- If you do not know something, say "I don't have that information, but I'll make sure the team follows up."
- If the stakeholder becomes hostile or requests to end the call, thank them and end gracefully.
- If the stakeholder asks a question outside your knowledge, acknowledge it and note it for follow-up.

## Information Extraction Targets
Listen for and confirm these when naturally possible:
- Stakeholder's actual role and decision authority
- Budget signals (positive, negative, or unclear)
- Timeline signals (urgency, delays, deadlines)
- Competitor mentions
- Security or compliance requirements
- Procurement process details
- Names of other stakeholders or decision-makers
- Objections or concerns
- Agreed next steps

## Conversation Style
- Keep responses under 3 sentences when possible.
- Ask one question at a time.
- Summarize what you've heard before moving to a new topic.
- Always end by confirming the agreed next step.
```

#### 13.3.4 Hangup strategy

The agent should end the call when:
- All open questions for the call objective have been addressed (or explicitly declined)
- The stakeholder requests to end the call
- The stakeholder is unresponsive for 15+ seconds after two prompts
- The call has exceeded 8 minutes (gracefully wrap up)
- The stakeholder redirects to email-only communication

Closing script: "Thank you for your time, {stakeholder_name}. I'll make sure the team has all of this documented. Have a great day."

#### 13.3.5 Dynamic context passing

The backend composes a `user_data` JSON object at call initiation time containing:
- Current deal snapshot summary
- Target stakeholder profile
- Call objective enum and human-readable description
- Top 2 open questions from the deal state
- Known context from prior calls (from memory retrieval)
- Any specific topics flagged by the user in the call modal

Context caps for the voice agent:

- `deal_context` must be capped to a concise summary of at most 3 sentences
- `open_questions` must be capped to the 2 most critical questions for the selected objective
- `known_context` should be compressed to only the highest-value facts needed for the next call

This `user_data` is sent in the Bolna API call request body. The agent's system prompt on Bolna uses these fields as template variables.

#### 13.3.6 Agent configuration on Bolna dashboard

Step-by-step setup:
1. Log in to Bolna dashboard (https://app.bolna.ai)
2. Navigate to "Agents" → "Create Agent"
3. Set agent name: "Signal Layer Discovery Agent"
4. Select LLM provider: OpenAI, model: GPT-4o
5. Select TTS provider: ElevenLabs, choose a professional voice
6. Paste the system prompt from Section 13.3.3 into the agent prompt field
7. Set the welcome message from Section 13.3.2
8. Configure webhook URL: `<WEBHOOK_BASE_URL>/api/webhooks/bolna`
9. Save and copy the Agent ID → set as `BOLNA_AGENT_ID` environment variable
10. Navigate to Developers tab → copy API key → set as `BOLNA_API_KEY` environment variable

---

## 14. Functional Requirements

### 14.1 Authentication and access

V1 requirements:

- Seed one organization
- Support at least one operator user
- Basic login for protected routes
- Role model can be minimal: `admin` and `operator`

Out of scope:

- SSO
- SCIM
- Fine-grained permissions

### 14.2 Deal workspace

The deal page must show:

- Deal name
- Account name
- Stage
- Risk score and risk level
- Coverage status
- Open questions
- Stakeholder list
- Call timeline
- Recent extracted signals
- Latest recommendation
- Follow-up drafts

Acceptance criteria:

- User can view a deal and its stakeholders in one page
- Risk is visible without opening raw transcripts
- The latest recommendation is visible with reasoning

### 14.3 Stakeholder management

Each stakeholder should support:

- Name
- Title
- Department
- Email
- Phone
- Role in buying process
- Stance and sentiment
- Last contacted timestamp
- Confidence
- Known vs inferred source

Acceptance criteria:

- User can add and edit a stakeholder manually
- System can infer new stakeholder candidates from call content
- UI distinguishes manually entered and inferred data

### 14.4 Outbound call initiation

Requirements:

- User selects a stakeholder and a call objective
- Backend composes dynamic context from deal memory
- Call initiation creates a `CallSession` immediately
- The call uses Bolna for actual dialing and voice interaction
- Failures are surfaced cleanly to the UI

Call objective examples:

- Discover buying process
- Validate timeline
- Identify economic buyer
- Clarify an objection
- Re-engage a stalled stakeholder
- Recover a next step

Acceptance criteria:

- User can initiate a real outbound call from the deal page
- Call session transitions through a clear state machine
- Duplicate initiation attempts are handled safely

### 14.5 Real-time call monitoring

During an active call, the system should surface:

- Current call state from provider webhooks and/or execution polling, pushed to the frontend via WebSocket
- Call duration when the provider exposes enough timing metadata to compute it safely
- Transcript text after call completion as the canonical V1 behavior
- Partial transcript updates only if captured Bolna payloads for the configured agent prove they are available during the call

**Important:** V1 should be designed around reliable status updates plus post-call transcript delivery. Live transcript streaming is optional and must not be assumed until verified against real Bolna payloads in your own account.

The post-call intelligence pipeline (extraction → risk → recommendation) is the primary "wow moment." Live transcript streaming is a best-effort enhancement, not the core value proposition.

Acceptance criteria:

- UI updates without full page refresh
- Call status transitions are reflected within 2 seconds of webhook receipt or polling refresh
- Important events are timestamped
- Transcript is visible after call completion at minimum
- If partial transcripts are available during the call, they are displayed incrementally
- While a call or extraction is in an active state, the frontend re-polls the relevant call and deal read models every 5 seconds
- On WebSocket reconnect, the frontend immediately invalidates and re-fetches the active call and deal queries

### 14.6 Post-call intelligence

After a call, the system must produce:

- Structured extraction
- Evidence anchors for important claims
- Updated stakeholder state
- Updated deal snapshot
- Updated risk snapshot
- At least one next-best action
- Follow-up drafts (including `draft_type = "crm_note"` — a plain-text CRM-ready summary the user can paste into Salesforce, HubSpot, or similar)

Acceptance criteria:

- Transcript storage succeeds even if extraction fails
- Failed downstream jobs are retryable
- User can inspect why a recommendation was made
- CRM note draft is generated alongside email/follow-up drafts

### 14.7 Semantic memory

The system must store vectorized memory documents in `pgvector`.

Memory document types:

- Call summary
- Objection summary
- Stakeholder profile summary
- Deal state summary
- Action rationale summary

Search modes:

- Similar calls within the same deal
- Similar stakeholders within the same account
- Similar objections across deals
- Similar risk patterns across prior snapshots

Acceptance criteria:

- New memory documents are embedded automatically
- Search returns ranked results with scores
- Memory evidence can be shown in debug mode
- Initial risk update and first recommendation after a call must not wait for the new embedding write to finish

### 14.8 Risk engine

The system must compute an interpretable risk score from signals and heuristics.

Minimum risk inputs:

- No clear next step
- No identified economic buyer
- Single-threaded account
- Negative or declining sentiment
- Repeated unresolved objection
- Security, legal, or procurement blocker
- Timeline slippage
- Budget uncertainty
- Long inactivity gap

Outputs:

- Numeric risk score
- Risk level
- Top factors
- Delta vs previous snapshot
- Evidence anchors for critical factors

Acceptance criteria:

- Risk updates after every processed call
- User can inspect the major factors
- Risk history is stored over time

### 14.9 Next-best action engine

The system must recommend at least one action after each successfully processed call.

Possible actions:

- Call a specific stakeholder
- Send a follow-up email
- Ask for procurement introduction
- Send security collateral
- Confirm timeline
- Escalate to AE or manager
- Book a multi-threaded meeting
- Deprioritize the deal

Each recommendation must include:

- Action type
- Target stakeholder if applicable
- Reasoning
- Confidence
- Suggested talk track or email
- Deadline or urgency

Acceptance criteria:

- Recommendation references current deal state
- Recommendation can be accepted, dismissed, or edited
- Recommendation still generates if vector retrieval is unavailable
- Recommendation generation after a call may use prior persisted memory, and must not block on embedding the current call

### 14.10 Timeline and auditability

Every important event must appear in a timeline:

- Deal created
- Stakeholder added or updated
- Call initiated
- Call answered
- Transcript received
- Extraction completed
- Risk updated
- Recommendation created
- Follow-up draft generated
- Manual override applied

Acceptance criteria:

- Timeline is visible on the deal page
- Events are ordered by timestamp
- Developer mode can reveal raw payloads and artifact metadata

### 14.11 Settings and debug

V1 settings should support:

- Prompt template version selection
- Risk weighting configuration
- Debug mode for evidence and memory inspection
- Provider and webhook status visibility

---

## 15. End-to-End System Flow

### 15.1 Call initiation flow

1. Frontend sends `POST /api/deals/{deal_id}/calls`.
2. API validates user, stakeholder, and objective.
3. API creates `CallSession(status=initiating)`.
4. API builds a call context package from the latest deal and stakeholder snapshots.
5. API invokes the Bolna adapter.
6. API stores provider request and response metadata.
7. API returns `call_id` immediately.

### 15.2 Webhook ingestion flow

1. Bolna sends a webhook event.
2. API validates signature if supported.
3. API checks a Redis idempotency key and exits safely if the payload was already processed.
4. API persists the raw payload and deduplication key.
5. API sends the raw payload through a shared Bolna ingestion entry point used by both webhooks and polling responses.
6. API normalizes the payload into an internal event.
7. API updates the call read model.
8. API publishes a lightweight real-time message.
9. API enqueues any heavier downstream processing.

Polling results must go through this same ingestion, idempotency, and normalization path to avoid duplicate processing when both webhook and polling observe the same terminal call state.

### 15.3 Post-call processing flow

1. API enqueues a durable processing job after transcript finalization or terminal call completion.
2. Worker dequeues the job and normalizes transcript content.
3. Worker runs extraction and schema validation.
4. Worker writes extraction snapshot and evidence anchors.
5. Worker acquires a row-level lock on the target deal before mutating deal-level projections or snapshots.
6. Worker launches memory document generation and embedding as a non-blocking branch that does not gate the first risk update.
7. Worker recomputes stakeholder and deal snapshots.
8. Worker runs risk scoring using the latest extraction plus the previous persisted state, not the just-created vector index.
9. Worker generates recommendations and follow-up drafts (including CRM note).
10. Worker publishes refreshed UI events via WebSocket.
11. Worker marks the embedding branch complete when that async branch finishes.

Note: In V1, this worker still runs on the same node as the API. Reliability comes from durable queue semantics, not from distributing across machines.

---

## 16. State Models

### 16.1 Call session state machine

Allowed call states:

- `initiating`
- `queued`
- `ringing`
- `in_progress`
- `completed`
- `no_answer`
- `busy`
- `failed`
- `canceled`

Rules:

- State changes are append-only in `CallEvent`
- `CallSession.status` is the latest projection
- Unknown provider events are persisted but do not break processing

### 16.2 Processing state machine

Separate from call state, each call has an intelligence processing state:

- `pending`
- `transcript_partial`
- `transcript_finalized`
- `extraction_running`
- `extraction_completed`
- `snapshots_updating`
- `risk_running`
- `recommendation_completed`
- `failed_retryable`
- `failed_terminal`

This separation avoids coupling call delivery status with AI processing status.

`snapshots_updating` covers the locked section where stakeholder and deal snapshots are recomputed before risk evaluation begins.

### 16.3 Recommendation lifecycle

- `proposed`
- `accepted`
- `dismissed`
- `edited`
- `expired`

### 16.4 Manual override behavior

If a user edits extracted fields, risk factors, or recommendations:

- The edit must be stored with actor and timestamp
- The previous AI-generated artifact must remain available
- UI should indicate human-edited vs AI-generated state

---

## 17. Data Model

### 17.1 Modeling approach

The system uses three layers of data:

- Raw immutable inputs such as provider payloads and transcript utterances
- Versioned AI artifacts such as extraction and risk snapshots
- Read models such as current deal risk and stakeholder state for fast UI access

### 17.2 Core entities

**Implementation tier annotations:**

- **Core (always needed for V1):** Organization, User, Deal, Stakeholder, CallSession, CallEvent, TranscriptUtterance, ExtractionSnapshot, EvidenceAnchor, StakeholderSnapshot, DealSnapshot, RiskSnapshot, ActionRecommendation, FollowupDraft, MemoryDocument
- **Enhanced (implement if time permits, otherwise simplify):** AuditLog
- **Full (deferred or simplified initially):** Additional analytics and derived read models beyond the entities listed below

These annotations do not remove any entity from the data model. They guide implementation prioritization. Evidence anchors, snapshots, follow-up drafts, and pgvector-backed memory are Core because they are part of the V1 processing pipeline and acceptance criteria.

#### Organization

- `id`
- `name`
- `created_at`

#### User

- `id`
- `org_id`
- `name`
- `email`
- `password_hash`
- `role`
- `created_at`

#### Deal

- `id`
- `org_id`
- `name`
- `account_name`
- `stage`
- `owner_user_id`
- `risk_score_current`
- `risk_level_current`
- `coverage_status_current`
- `summary_current`
- `created_at`
- `updated_at`

#### Stakeholder

- `id`
- `deal_id`
- `name`
- `title`
- `department`
- `email`
- `phone`
- `role_label_current`
- `role_confidence_current`
- `stance_current`
- `sentiment_current`
- `last_contacted_at`
- `source_type` (`manual` or `inferred`)
- `metadata_json`
- `created_at`
- `updated_at`

#### CallSession

- `id`
- `deal_id`
- `stakeholder_id`
- `provider_name`
- `provider_call_id`
- `status`
- `processing_status`
- `objective`
- `initiated_by_user_id`
- `started_at`
- `ended_at`
- `duration_seconds`
- `recording_url` nullable
- `provider_metadata_json`
- `created_at`
- `updated_at`

#### CallEvent

- `id`
- `call_session_id`
- `provider_event_id`
- `event_type`
- `event_timestamp`
- `sequence_number` nullable
- `payload_json`
- `created_at`

#### TranscriptUtterance

- `id`
- `call_session_id`
- `provider_segment_id` nullable
- `speaker`
- `text`
- `start_ms`
- `end_ms`
- `sequence_number`
- `is_final`
- `created_at`

#### ExtractionSnapshot

- `id`
- `call_session_id`
- `schema_version`
- `prompt_version`
- `model_name`
- `extracted_json`
- `summary`
- `confidence`
- `created_at`

#### EvidenceAnchor

- `id`
- `call_session_id`
- `artifact_type`
- `artifact_id`
- `field_name`
- `transcript_utterance_id` nullable
- `quote_text`
- `speaker`
- `sequence_number`
- `confidence`
- `created_at`

#### StakeholderSnapshot

- `id`
- `stakeholder_id`
- `summary`
- `role_label`
- `role_confidence`
- `stance`
- `sentiment`
- `open_questions_json`
- `created_at`

#### DealSnapshot

- `id`
- `deal_id`
- `summary`
- `coverage_status`
- `open_questions_json`
- `key_signals_json`
- `created_at`

#### RiskSnapshot

- `id`
- `deal_id`
- `call_session_id` nullable
- `score`
- `level`
- `factors_json`
- `change_summary_json`
- `model_metadata_json`
- `created_at`

#### ActionRecommendation

- `id`
- `deal_id`
- `call_session_id` nullable
- `target_stakeholder_id` nullable
- `action_type`
- `reason`
- `confidence`
- `status`
- `payload_json`
- `created_at`
- `updated_at`

#### FollowupDraft

- `id`
- `deal_id`
- `call_session_id`
- `draft_type`
- `subject` nullable
- `body_text`
- `tone`
- `status`
- `created_at`
- `updated_at`

#### MemoryDocument

- `id`
- `deal_id`
- `stakeholder_id` nullable
- `call_session_id` nullable
- `doc_type`
- `content`
- `metadata_json`
- `embedding`
- `created_at`

#### AuditLog

- `id`
- `entity_type`
- `entity_id`
- `action`
- `actor_user_id` nullable
- `payload_json`
- `created_at`

### 17.3 Data integrity requirements

- `provider_event_id` must be unique when the provider supplies one
- Webhook deduplication must not rely only on in-memory state
- Snapshots are append-only
- Current deal and stakeholder values are projections, not the only source of truth
- Deal-level projection updates after call completion must use a row-level lock such as `SELECT ... FOR UPDATE` on the deal row to prevent concurrent snapshot races

---

## 18. AI System Design

### 18.1 Extraction pipeline

The extraction pipeline transforms transcript text into a normalized schema and rejects malformed outputs before persistence.

Implementation hardening requirements:

- Use the `google-genai` structured output path with the Pydantic extraction schema supplied as the response schema
- Catch schema validation failures explicitly
- Retry invalid structured outputs up to 2 times using `tenacity`
- On each validation retry, include the validation error summary in the repair prompt so the model can correct missing or malformed fields
- Only mark the extraction job `failed_retryable` after the retry budget is exhausted

Core requirements:

- Strict schema validation
- `unknown` instead of guessing
- Explicit separation of observed vs inferred facts
- Confidence values for major fields
- Evidence anchors for critical claims
- SDK-level structured output enforcement using the declared response schema
- Validation-aware retry behavior before a call is marked `failed_retryable`

Minimum extraction schema:

```json
{
  "stakeholder": {
    "name": "string",
    "title": "string",
    "role_label": "champion|blocker|economic_buyer|influencer|procurement|legal|unknown",
    "role_confidence": 0.0
  },
  "qualification": {
    "budget_signal": "positive|negative|unknown",
    "authority_signal": "positive|negative|unknown",
    "need_signal": "positive|negative|unknown",
    "timeline_signal": "positive|negative|unknown"
  },
  "deal_signals": {
    "pain_points": ["string"],
    "objections": ["string"],
    "competitors": ["string"],
    "security_mentions": ["string"],
    "procurement_mentions": ["string"],
    "next_step": "string",
    "timeline_detail": "string",
    "budget_detail": "string"
  },
  "interaction": {
    "sentiment": "positive|neutral|negative",
    "engagement_level": "high|medium|low",
    "followup_requested": true
  },
  "evidence": [
    {
      "field": "next_step",
      "quote": "string",
      "speaker": "prospect",
      "sequence_number": 12
    }
  ],
  "summary": "string",
  "confidence": 0.0
}
```

### 18.2 Memory strategy

Memory documents to embed:

- Full call summary
- Objection-only summary
- Stakeholder profile summary
- Deal state summary
- Action rationale summary

Retrieval modes:

- Similar calls within the same deal
- Similar stakeholders within the same account
- Similar objections across deals
- Similar risk patterns across historical calls

Rules:

- Memory writes are asynchronous
- Retrieval is advisory, not required for core risk scoring
- Retrieval failure must degrade gracefully

### 18.3 Risk engine

The risk engine uses a hybrid model:

- Deterministic rules for core risks
- Snapshot diffs for change detection
- LLM-generated narrative explanation grounded in current evidence

Example risk factors:

- No decision-maker identified
- No next step defined
- Single-threaded account
- Negative sentiment increase
- Timeline slippage
- Unresolved procurement, security, or legal issue
- Repeated objection without mitigation
- Long inactivity since last contact

Example output:

```json
{
  "risk_score": 74,
  "risk_level": "high",
  "top_factors": [
    "No clear economic buyer identified",
    "Security review blocker raised",
    "No committed next step"
  ],
  "change_since_last_snapshot": [
    "Risk increased by 12 points",
    "New blocker: security review"
  ]
}
```

### 18.4 Recommendation engine

Inputs:

- Current deal snapshot
- Latest extraction
- Latest risk snapshot
- Relevant memory documents
- Stakeholder coverage gaps

Outputs:

- Next best action
- Target stakeholder
- Explanation
- Suggested talk track
- Suggested follow-up email or note

Policy examples:

- If no economic buyer is identified, recommend asking for or contacting the economic buyer.
- If a champion exists but procurement blocker appears, recommend procurement-focused follow-up.
- If the stakeholder asked for email only, generate the email and mark the call action complete.
- If risk is critical and there has been no response for 14 days, recommend escalation.

### 18.5 Prompting requirements

Voice agent prompt goals:

- Sound concise and professional
- Use dynamic account context
- Pursue one clear objective per call
- Confirm important details explicitly
- Avoid hallucinating company facts
- Escalate gracefully when uncertain

Extraction prompt goals:

- Enforce strict JSON schema
- Ground claims in transcript evidence
- Prefer `unknown` over speculation
- Separate explicit and inferred signals
- Return confidence by field group

Recommendation prompt goals:

- Use current state plus latest call context
- Prefer concrete actions over generic advice
- Explain why the recommendation matters
- Include fallback guidance when confidence is low

### 18.6 Artifact versioning

Every persisted AI artifact must capture:

- `schema_version`
- `prompt_version`
- `model_name`
- `created_at`

This is required for debugging, reprocessing, and evaluation.

---

## 19. Realtime and Eventing

### 19.1 Internal event types

The backend should normalize provider-specific payloads into internal event types such as:

- `call.initiated`
- `call.queued`
- `call.ringing`
- `call.started`
- `call.completed`
- `call.busy`
- `call.no_answer`
- `call.canceled`
- `call.failed`
- `transcript.partial`
- `transcript.final`
- `extraction.completed`
- `risk.updated`
- `recommendation.created`

Notes:

- `transcript.partial` is reserved for forward compatibility. V1 does not require a handler for it unless captured Bolna payloads prove mid-call transcript segments are available.

### 19.2 Real-time delivery to frontend

The frontend subscribes over WebSocket to:

- `/ws/deals/{deal_id}`
- `/ws/calls/{call_id}`

WebSocket payloads should be lightweight and point the frontend to re-fetch durable state when needed.

Frontend resilience rules:

- WebSockets are hints, not the source of truth
- While a call or extraction is active, the frontend must poll the relevant read models every 5 seconds
- On WebSocket reconnect, the frontend must immediately invalidate and re-fetch the active call and deal queries

### 19.3 Reliability rules

- Webhook writes must be durable before acknowledgment
- Event processing must be idempotent
- Event order should be handled defensively
- Duplicate transcript segments must not create duplicate final utterances

---

## 20. API Surface

### 20.0 Auth endpoints

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `POST /api/auth/refresh` optional

### 20.1 Deal endpoints

- `POST /api/deals`
- `GET /api/deals`
- `GET /api/deals/{deal_id}`
- `PATCH /api/deals/{deal_id}`

### 20.2 Stakeholder endpoints

- `POST /api/deals/{deal_id}/stakeholders`
- `GET /api/deals/{deal_id}/stakeholders`
- `PATCH /api/stakeholders/{stakeholder_id}`
- `DELETE /api/stakeholders/{stakeholder_id}`

### 20.3 Call endpoints

- `POST /api/deals/{deal_id}/calls`
- `GET /api/calls/{call_id}`
- `GET /api/calls/{call_id}/timeline`
- `GET /api/calls/{call_id}/transcript`

### 20.4 Intelligence endpoints

- `GET /api/deals/{deal_id}/risk`
- `GET /api/deals/{deal_id}/recommendations`
- `POST /api/recommendations/{recommendation_id}/accept`
- `POST /api/recommendations/{recommendation_id}/dismiss`
- `PATCH /api/recommendations/{recommendation_id}`
- `GET /api/deals/{deal_id}/drafts`

### 20.5 Memory endpoints

- `GET /api/deals/{deal_id}/memory/search`
- `GET /api/deals/{deal_id}/memory/similar-calls`
- `GET /api/stakeholders/{stakeholder_id}/memory`

### 20.6 Webhook and health endpoints

- `POST /api/webhooks/bolna`
- `GET /api/health/live`
- `GET /api/health/ready`

### 20.7 Rate limiting and throttling requirements

V1 must implement explicit request throttling and concurrency controls.

Minimum controls:

- `POST /api/deals/{deal_id}/calls` must be rate-limited per authenticated user and per target stakeholder
- Auth endpoints must have brute-force protection
- Polling fallback for Bolna executions must be capped and back off automatically
- LLM and embedding requests must have provider-aware concurrency caps and retry behavior for `429` or quota errors
- Worker concurrency must be bounded so one burst of calls does not starve the node

Recommended V1 defaults:

- Call initiation: maximum 3 attempts per user per 10 minutes
- Call initiation to the same stakeholder: maximum 1 active or recently initiated call within 5 minutes unless an admin overrides it
- Auth login attempts: maximum 5 failed attempts per IP per 15 minutes, then temporary cooldown
- Execution polling: default every 5 seconds with exponential backoff and a hard stop after terminal call state
- Extraction concurrency: configurable worker limit, default 2 concurrent post-call pipelines on a single-node deployment
- Recommendation concurrency: configurable limit, default shares the same worker pool as extraction

Behavior:

- Rate-limited user actions must return `429 Too Many Requests` with a machine-readable retry hint
- The UI should show a clear throttle message instead of a generic error
- Admin users may have higher limits, but webhook ingestion must not depend on user-scoped rate limits

---

## 21. Frontend Requirements

### 21.1 Pages

#### `/login`

Authentication page:

- Email and password form
- Error and lockout feedback
- Redirect to primary workspace on success

#### `/`

Dashboard:

- List deals
- Show risk badges
- Show latest activity
- Create deal CTA

#### `/deals/[dealId]`

Primary workspace:

- Deal header
- Stakeholder panel
- Risk panel
- Open questions panel
- Action center
- Timeline
- Transcript drawer
- "Call with AI" modal

#### `/calls/[callId]`

Live call view:

- Call state
- Transcript feed
- Extraction progress
- Important alerts
- Post-call summary

#### `/settings`

- Prompt template selection
- Risk weighting controls
- Debug toggles
- Provider health visibility

### 21.2 UX requirements

- Primary action is visible above the fold
- Risk explanation is visible without expanding debug panels
- Transcript supports incremental updates
- Raw evidence is expandable, not always visible
- AI-generated content is clearly labeled with "inspect evidence" expandable sections
- Loading states explain background processing

#### 21.2.1 Required empty, loading, and error states

- **Empty deal list:** CTA to create the first deal
- **No stakeholders:** prompt to add the first stakeholder
- **No calls yet:** prompt to initiate the first call with a stakeholder
- **Call in progress:** loading animation with call status text and duration timer
- **Extraction running:** engaging multi-step progress indicator driven by backend processing state (e.g., "Analyzing transcript..." -> "Computing risk..." -> "Drafting follow-up...")
- **Extraction failed:** error state with retry option and link to raw transcript
- **No recommendations yet:** placeholder explaining recommendations appear after the first call
- **AI-generated content:** clearly labeled as AI-generated, with confidence indicator where applicable

#### 21.2.2 Real-time state recovery

- If a user returns to the tab, reconnects after sleep, or changes networks mid-call, the UI must recover by refetching active call and deal state rather than waiting indefinitely on a stale WebSocket
- Active-state polling should automatically stop once the call and extraction reach terminal states

### 21.3 V1 design note

The stakeholder graph should be a stretch enhancement, not a dependency for V1 completeness. A strong list-based workspace with evidence-driven panels is more important than a visually complex graph.

---

## 22. Security, Privacy, and Compliance

### 22.1 Security requirements

- Secrets live in environment variables, never in frontend bundles
- Webhook verification must be implemented if Bolna supports signatures
- Protected routes require auth
- Raw provider payloads must be access-controlled
- Admin and operator access should be separated at least minimally
- Auth and call-triggering endpoints must enforce rate limits appropriate to abuse resistance and provider cost control

### 22.1.1 Abuse prevention and ingress protection

- Auth endpoints must have brute-force protection and temporary lockout or cooldown behavior
- Call initiation must be throttled by user, stakeholder, and optionally source IP
- Webhook endpoint should not use normal user rate limiting, but it must use signature verification when available, payload deduplication, ingress throttling, and request size limits
- Reverse proxy or API gateway should enforce coarse ingress limits to protect the single-node deployment from burst traffic

### 22.2 Privacy requirements

- Store only the minimum PII needed for the workflow
- Mask phone numbers in non-admin views where possible
- Support transcript redaction for sensitive spans
- Support configurable retention for transcripts and recordings if recordings are stored

### 22.3 Call recording and legal notice

If recordings are enabled, the system must support a configurable disclosure strategy aligned with the laws relevant to the demo numbers and geography. This is an operational requirement, not a stretch feature.

### 22.4 Audit requirements

- Every manual edit must be audited
- Every AI artifact must be attributable to a model and prompt version
- Critical risk claims should have evidence anchors

---

## 23. Reliability and Operational Guardrails

### 23.1 Reliability rules

- Webhook processing is idempotent
- Background jobs are retry-safe
- Partial failures do not corrupt deal state
- Transcript storage does not depend on extraction success
- Recommendation generation does not depend on vector retrieval success
- Provider-facing and user-facing flows must degrade safely under quota exhaustion or burst load

### 23.2 Failure handling

Retryable failures:

- Temporary LLM failure
- Temporary embedding failure
- Temporary Redis outage
- Temporary provider API timeout
- Provider `429` or quota exhaustion events

Terminal failures:

- Invalid schema after retry budget
- Malformed provider payload with no recoverable fields
- Missing required domain objects after consistency checks

### 23.3 Dead-letter handling

Failed jobs that exceed retry budget must be written to a dead-letter queue or failure table for manual replay.

### 23.4 Graceful degradation

If some subsystems fail:

- Without embeddings: continue extraction, risk, and base recommendation
- Without WebSocket: allow manual refresh fallback
- Without recordings: transcript-based flow still works
- Under provider throttling: defer lower-priority jobs, preserve transcript and call state first, and surface delayed intelligence status in the UI

### 23.5 Rate-limit and quota handling

- All outbound provider adapters must implement exponential backoff with jitter for transient `429` and timeout responses
- Rate-limit state for user-triggered endpoints should live in Redis so limits survive API process restarts
- Webhook handlers must prefer deduplication and short ingress throttles over aggressive rejection, to avoid dropping legitimate provider retries
- Queue consumers must enforce bounded concurrency and should not dequeue more work than the node can process within SLA

---

## 24. Non-Functional Requirements

### 24.1 Performance

Targets for V1:

- Webhook acknowledgment p95 under 500 ms after durable write
- Deal page load p95 under 2 seconds in demo environment
- Live call state visible in UI within 2 seconds of webhook receipt
- Post-call extraction completed within 45 seconds of transcript finalization for typical demo calls
- Rate-limited requests should return a throttle response immediately without expensive downstream work

### 24.2 Maintainability

- Clear service boundaries
- Typed schemas end-to-end
- Minimal business logic in route handlers
- Feature flags for incomplete modules
- Prompt templates stored in a versioned way

### 24.3 Observability

- Structured logs
- Request IDs
- Job IDs
- Timeline of domain events
- Basic debug panel for raw events, snapshots, and recommendations

---

## 25. Testing and Evaluation

### 25.1 Unit tests

- Risk scoring rules
- Extraction normalization
- Recommendation policy helpers
- Snapshot diff logic

### 25.2 Integration tests

- Call initiation flow
- Webhook ingestion and deduplication
- Duplicate terminal webhook delivery does not create duplicate risk or recommendation artifacts
- Transcript normalization pipeline
- Post-call processing pipeline from transcript to risk snapshot
- Concurrent call completions for the same deal do not corrupt snapshots or projections

### 25.3 Frontend tests

- Deal workspace rendering
- Call page live-state updates with mocked WebSocket messages
- Active-state polling recovers the UI after WebSocket disconnect or reconnect
- Recommendation display and action handling

### 25.4 Manual demo checklist

- Seed deal exists
- Stakeholder has a real phone number
- Public webhook endpoint is reachable
- Bolna credentials configured
- Real outbound call succeeds
- Transcript visible in UI
- Risk changes after the call
- Recommendation and follow-up draft appear

---

## 26. Seed Demo Scenario

### 26.1 Scenario

Security blocker in a multi-stakeholder deal

### 26.2 Seed setup

Deal:

- `Acme Corp - AI Contact Center Upgrade`

Stage:

- `Discovery`

Stakeholders:

- Priya Sharma - Ops Manager - Champion
- Rahul Mehta - VP Operations - Decision-maker candidate
- Security Lead - Missing or not yet engaged

Initial risk reasons:

- No confirmed economic buyer
- Security review not addressed
- Next step unclear

### 26.3 Voice task

The agent calls Rahul Mehta or the Security Lead to uncover:

- Who approves vendor selection
- Whether security review is mandatory
- Expected timeline
- Procurement constraints

### 26.4 Expected post-call output

- Stakeholder role is updated
- Security blocker is identified or clarified
- Risk score changes
- Recommendation suggests sending security collateral or scheduling a security review
- Follow-up draft is generated

---

## 27. Acceptance Criteria

V1 is complete when all of the following are true:

- User can create and open a deal
- User can add and edit stakeholders
- User can trigger a real outbound Bolna voice call from the UI
- Backend persists call session, call events, and transcript segments
- UI reflects call progress in near real time
- Transcript is visible after call completion
- Structured extraction is generated and stored
- Evidence anchors exist for critical extracted claims
- Deal risk score updates automatically
- At least one next-best action is generated
- Follow-up draft is generated
- Timeline reflects the complete event sequence
- Demo can run end-to-end with seed data and real phone numbers

---

## 28. Engineering Notes for Implementation Planning

### 28.1 Recommended build order

1. Data model and migrations
2. Auth and seed data
3. Deal and stakeholder CRUD
4. Call initiation API and Bolna adapter
5. Webhook ingestion and raw event persistence
6. WebSocket updates
7. Transcript storage and display
8. Extraction pipeline
9. Risk engine
10. Recommendation engine
11. Memory retrieval with `pgvector`
12. Polish, observability, and demo hardening

### 28.2 Environment configuration

Required environment variables:

```
# Bolna Voice Provider
BOLNA_API_KEY          # From Bolna dashboard → Developers tab
BOLNA_AGENT_ID         # After agent creation on Bolna dashboard
BOLNA_MOCK_MODE=false
BOLNA_EXECUTION_POLL_INTERVAL_SECONDS=5
BOLNA_WEBHOOK_ALLOWED_IPS   # Optional comma-separated allowlist if Bolna provides fixed egress IPs for your account
BOLNA_EXECUTION_POLL_MAX_ATTEMPTS=24
WEBHOOK_IDEMPOTENCY_TTL_SECONDS=86400

# Google Gemini (Backend AI)
GEMINI_API_KEY         # For extraction, risk narrative, recommendation, and embeddings
GEMINI_MODEL_EXTRACTION=gemini-2.5-flash
GEMINI_MODEL_RECOMMENDATION=gemini-2.5-pro
GEMINI_MODEL_EMBEDDING=gemini-embedding-001
LLM_MAX_CONCURRENT_REQUESTS=2
LLM_VALIDATION_MAX_RETRIES=2

# Database
DATABASE_URL           # Postgres connection string (e.g., postgresql+asyncpg://user:pass@localhost:5432/signal_layer)

# Redis
REDIS_URL              # Redis connection string (e.g., redis://localhost:6379/0)
REDIS_RATE_LIMIT_PREFIX=signal_layer:ratelimit

# Auth
JWT_SECRET             # For auth token signing (generate a strong random value)
AUTH_MAX_FAILED_ATTEMPTS=5
AUTH_LOCKOUT_WINDOW_SECONDS=900

# Webhooks
WEBHOOK_BASE_URL       # Public URL for Bolna webhooks (use ngrok in development)
WEBHOOK_MAX_BODY_SIZE_MB=2

# Frontend
FRONTEND_URL           # For CORS configuration (e.g., http://localhost:3000)
NEXT_PUBLIC_API_URL    # API base URL for frontend requests
NEXT_PUBLIC_WS_URL     # WebSocket URL for real-time updates
NEXT_PUBLIC_ACTIVE_STATE_POLL_INTERVAL_MS=5000

# Application Rate Limits
CALL_INIT_MAX_PER_USER_WINDOW=3
CALL_INIT_WINDOW_SECONDS=600
CALL_INIT_STAKEHOLDER_COOLDOWN_SECONDS=300
WORKER_MAX_CONCURRENT_PIPELINES=2
``` 

### 28.3 Implementation guidance

- Use service classes, not route-heavy business logic
- Keep provider-specific logic behind adapters
- Define Pydantic schemas early
- Store raw provider payloads for debugging
- Use SDK-level structured outputs with the response schema instead of manual JSON scraping from model text
- Wrap extraction validation retries with `tenacity` and capture the last validation error for observability
- Add a demo seed script
- Add fixtures for transcript and extraction tests
- Add a mock mode for voice provider only as a local fallback, not as the primary demo path

### 28.4 Demo hardening

**Webhook delivery in development:**
- Use ngrok (`ngrok http 8000`) or Cloudflare Tunnel to expose the local backend to Bolna's webhook delivery.
- Set the resulting public URL as `WEBHOOK_BASE_URL` and configure it in the Bolna agent's webhook settings.
- Capture at least one real webhook payload and one execution polling response before finalizing the parser and status mapping in code.

**Seed script:**
- A CLI command (e.g., `python -m backend.scripts.seed`) that creates: one organization, one user (with login credentials), one deal ("Acme Corp - AI Contact Center Upgrade"), and 2-3 stakeholders with configurable phone numbers.
- Phone numbers should be configurable via environment variable or CLI argument so the demo uses real reachable numbers.

**Mock mode:**
- An optional mock Bolna adapter that simulates webhook events locally for testing without making real calls.
- Activated via `BOLNA_MOCK_MODE=true` environment variable.
- Produces realistic webhook payloads with a synthetic transcript after a configurable delay.
- The primary demo path always uses real Bolna calls; mock mode is for development and CI only.

**Demo recording checklist:**
1. Show deal workspace with seed data (~30s)
2. Initiate a call from the UI (~30s)
3. Show live call status in the UI (~60-120s depending on call)
4. Show post-call transcript appearing (~15s)
5. Show extraction results, risk update, and recommendation (~30s)
6. Show follow-up draft and CRM note (~15s)
7. Walk through evidence inspection (~30s)

**Fallback plan:** If a real call fails during recording, have a pre-seeded completed call flow (from mock mode) to demonstrate the post-call intelligence pipeline.

### 28.5 Out-of-scope but future-ready seams

- Multi-tenant org isolation
- CRM adapters for Salesforce and HubSpot
- Additional voice providers
- Additional channel types such as email and Slack

---

## 29. Next Steps

With this PRD finalized, proceed to implementation planning. The PRD provides sufficient specification for:

1. **Bolna agent setup** — buildable directly from Section 13.3
2. **Backend architecture** — data model, API surface, and processing pipeline are fully specified
3. **Frontend structure** — pages, UX states, and real-time requirements are defined
4. **AI pipelines** — extraction schema, risk engine, and recommendation engine are documented with provider decisions
5. **Demo scenario** — seed data, recording checklist, and fallback plan are ready

The implementation plan should define build phases, task breakdown, and acceptance gates for each phase.

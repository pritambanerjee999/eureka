# Eureka — Voice Physics Tutor

A real-time voice AI tutor built on LiveKit. Sign in, pick a physics topic (or let Eureka assess your level), and talk it through — Eureka teaches the way Feynman did: intuition first, analogy before equation, and Socratic questions to check you actually got it.

---

## Running it

```bash
cp .env.example .env
# Fill in LIVEKIT_API_KEY, LIVEKIT_API_SECRET, LIVEKIT_URL, OPENAI_API_KEY
# and set JWT_SECRET (e.g. `openssl rand -hex 32`)
docker compose up --build
```

Open `http://localhost:3000`, click **Create an account**, choose a username and password, then pick a topic and start speaking. All secrets and configuration are read from the root `.env` (see `.env.example` for every variable).

---

## Architecture

```
Browser (Next.js :3000)
  │
  ├── POST /auth/register | /auth/login ──► FastAPI (api :8000) ──► PostgreSQL (users)
  │        ◄── JWT
  │
  ├── POST /token  (Bearer JWT) ──► FastAPI
  │                                   ├── creates session:{room} (identity, topic) ──► Redis
  │                                   ├── signs LiveKit room token
  │                                   └── dispatches agent "eureka-tutor" to the room ──► LiveKit Cloud
  │
  ├── GET /history, /notes  (Bearer JWT) ──► FastAPI ──► PostgreSQL
  │
  └── WebRTC audio ◄──────────────► LiveKit Cloud ◄────► Agent worker (agent)
                                                            ├── Silero VAD
                                                            ├── OpenAI Whisper (STT)
                                                            ├── GPT-4o (LLM + tools)
                                                            ├── OpenAI TTS
                                                            └── every turn ──► Redis conversation:{room}  (live state)
                                                                          └──► PostgreSQL conversations (history)
```

Five Docker services: `redis`, `postgres`, `api`, `agent`, `frontend`. The browser calls the API to authenticate and get a room token, then talks to LiveKit Cloud directly over WebRTC. The agent worker joins the same room and runs the voice pipeline.

**Separation of concerns**

| Concern | Where |
|---|---|
| Auth & users | `backend/api/routers/auth.py`, `services/auth_service.py`, `dependencies.py` |
| Session management | `backend/api/services/session_service.py` (Redis `session:{room}`), `routers/token.py` (token + dispatch) |
| Conversation handling | `backend/agent/services/conversation_service.py` — routes each turn to Redis + PostgreSQL, restores a room's live context |
| Voice / AI layer | `backend/agent/main.py` (pipeline + events), `agent.py` (tutor behaviour, tools), `prompts.py` |
| UI | `frontend/src/app/page.tsx`, `components/` |

**State**

| Store | Key / table | Holds | Lifetime |
|---|---|---|---|
| Redis | `session:{room}` (hash) | identity, topic, status — written by the API, read by the agent on join | 2 h TTL |
| Redis | `conversation:{room}` (list) | the live conversation for that room, one JSON turn per entry, capped at 200 | 24 h TTL |
| Redis | `active_rooms` (set) | live room names | — |
| PostgreSQL | `users` | username, scrypt password hash | durable |
| PostgreSQL | `conversations` | every turn plus `session_start`, `checkpoint`, `level` records, keyed by user | durable |
| PostgreSQL | `notes` | the student's notes per session | durable |

---

## Product features (and why)

- **Accounts.** Username/password sign-up and login. Everything — history, notes, assessed level — belongs to the account, so it follows you across browsers and devices.
- **Chat-style history sidebar.** Past sessions sit in a left sidebar grouped by *Today / Yesterday / Previous 7 days / Older*, like a chat app. Click one to reread the transcript, see what you understood and your notes, and **Continue this topic** with one click. History buried at the bottom of a page doesn't get used; a sidebar does.
- **Level picker + spoken assessment.** Five levels (Spark → Singularity) tune the topic suggestions. **Assess My Level** runs a three-question spoken calibration; the agent saves the result with a tool call and the UI preselects it next time.
- **Topic grid.** Five branches of physics with level-appropriate starter questions. Clicking one starts a session where Eureka speaks first: one vivid hook, three directions to explore, and a question about which one you want.
- **Understanding checkpoints.** When a student explains a concept in their own words, the agent calls `save_progress`, and the result shows up as a ✓ badge in history. This rewards understanding rather than time spent.
- **Live session view.** Agent state visualizer (listening / thinking / speaking), live transcript, a notes pad that autosaves per session, and links to curated references (Feynman Lectures, HyperPhysics, PhET…).
- **Resilient sessions.** If an agent drops and is redispatched to the same room, it rebuilds its context from Redis and picks up where it left off instead of starting over.

---

## Key design decisions and tradeoffs

**Separate FastAPI service instead of Next.js route handlers.** This keeps LiveKit credentials and the JWT secret off the frontend, makes the session/auth layer independently testable and deployable, and gives a clean boundary between session management and the UI.

**STT → LLM → TTS pipeline instead of GPT-4o Realtime.** The pipeline adds latency (roughly 300–600 ms per turn) but gives independent control of each stage: swap voices, change STT settings or change models without touching the rest, and get text transcripts for free, which history and checkpoints depend on. For a tutor, the quality of the explanation matters more than shaving off the last few hundred milliseconds.

**Redis for live conversation state, PostgreSQL for durable history.** Redis holds what's hot and room-scoped: session metadata and the running conversation. Writes are O(1) (`RPUSH`), the list is capped (`LTRIM`), and it expires on its own. PostgreSQL holds what must outlive a session: users, per-user history and notes. Each turn is written to both concurrently, and a failure in one store is logged and never blocks the other. The cost is two writes per turn, which is cheap next to an STT/LLM/TTS round trip.

**Explicit, named agent dispatch.** In LiveKit, an unnamed worker is automatically dispatched to every new room. Combined with an explicit dispatch from `/token`, that put two agents (two overlapping voices) in each room. The worker now registers as `eureka-tutor`, which disables automatic dispatch, and `/token` dispatches exactly one agent by name.

**Auth: stateless JWT, stdlib scrypt, username as identity.** HS256 JWTs (7-day expiry) mean the API needs no session lookup per request and scales horizontally. Passwords are hashed with `hashlib.scrypt` (memory-hard, per-user salt), so there's no native dependency. The username doubles as the LiveKit participant identity, so the browser can never choose who it is: `/token` ignores any client-supplied identity, and `/history` and `/notes` return 403 for anyone else's data. Login errors are identical for unknown users and wrong passwords, to avoid revealing which usernames exist. *Tradeoff:* the token is kept in `localStorage`, which is simpler but readable by an XSS bug. An httpOnly cookie plus CSRF protection would be the production choice.

**Tools for state the UI needs.** Level and checkpoints are saved through LLM tool calls (`save_level`, `save_progress`) rather than by parsing transcripts, so the model decides when real understanding happened and the data arrives structured.

**Why Feynman-style physics.** Physics has a clear topic structure and benefits enormously from analogy and Socratic checking. A tutor that *checks understanding* instead of *delivering information* is a better product, and physics is where that gap is largest.

---

## Scaling to 10,000 concurrent sessions

| Layer | Today | At 10k sessions |
|---|---|---|
| **Agent workers** | 1 container | The bottleneck. Each session runs a live VAD/STT/LLM/TTS pipeline, so target roughly 25–50 sessions per 4-vCPU container, which means 200–400 containers autoscaled on worker load. LiveKit Cloud already balances job dispatch across all registered `eureka-tutor` workers. |
| **API** | 1 Uvicorn process | Stateless (JWT auth, no in-process session state). Run multiple workers per pod behind a load balancer and scale horizontally. Add rate limiting on `/auth/*` and `/token`. |
| **Redis** | Single node, new connection per call | Use a shared connection pool in both services (today each call opens a connection, which is fine for a demo but too much churn at scale). Live data is small: 10k rooms × 200 turns × ~300 B ≈ 600 MB, so one node with a replica works; move to Redis Cluster sharded by room for headroom and failover. |
| **PostgreSQL** | Single instance, pool of 5 | Put PgBouncer in front, size the pools, and add a read replica for history and notes reads. Partition `conversations` by month (or by user hash). Batch turn inserts from the agent if write volume demands it. |
| **LiveKit** | LiveKit Cloud | Already distributed. If self-hosting, run LiveKit in cluster mode with a TURN fleet. |
| **OpenAI** | Per-turn API calls | Raise org rate limits, add retry with backoff, and consider cheaper or faster models (e.g. `gpt-4o-mini`, streaming TTS) for simple turns. Cost, not compute, becomes the main constraint. |

---

## Testing

All external services (PostgreSQL, Redis, LiveKit, OpenAI) are mocked.

```bash
docker exec eureka-api-1   python -m pytest /app/tests/ -q   # API: auth, token, history, schemas
docker exec eureka-agent-1 python -m pytest /app/tests/ -q   # Agent: tutor behaviour, conversation routing, stores
# Frontend (the runtime image has no dev deps, so run Jest in a throwaway Node container):
cd frontend && docker run --rm -v "$PWD":/app -v eureka_fe_node_modules:/app/node_modules -w /app \
  node:20-alpine sh -c "npm install && npx jest"
```

---

## Known limitations

- `/token` still accepts an optional client-supplied `room_name`. The UI never sends one; production would drop the field or check room ownership.
- History recorded before accounts existed (anonymous `user-xxxx` identities) isn't linked to any account. The `user-` username prefix is reserved so those records can't be claimed by accident.
- No password reset or email verification. Sessions last until the JWT expires (7 days) or the user logs out.

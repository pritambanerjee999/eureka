# Eureka — Voice Physics Tutor

A real-time voice AI tutor built on LiveKit. Sign in, pick a physics topic (or let Eureka assess your level), and talk it through. Eureka teaches the way Feynman did: intuition first, analogy before equation, and Socratic questions to check you actually got it.

**Contents:** [Run it](#run-it-step-by-step) · [Test it](#test-it) · [Troubleshooting](#troubleshooting) · [Architecture](#architecture) · [Features](#product-features-and-why) · [Design decisions](#key-design-decisions-and-tradeoffs) · [Scaling](#scaling-to-10000-concurrent-sessions) · [Limitations](#known-limitations)

---

## Run it, step by step

Everything runs in Docker. You don't need Python or Node installed.

### 0. Prerequisites

| You need | Check / get it |
|---|---|
| **Git** | `git --version` |
| **Docker with Compose v2** (Docker Desktop on macOS/Windows, or Docker Engine + compose plugin on Linux) | `docker compose version` should print v2.x. Docker must be running. |
| **Free ports 3000 and 8000** on your machine | The frontend and API listen there. (Postgres and Redis are internal only.) |
| **A LiveKit Cloud project** (free) | Sign up at https://cloud.livekit.io |
| **An OpenAI API key with billing enabled** | https://platform.openai.com/api-keys. The key needs access to `gpt-4o`, `whisper-1` and `gpt-4o-mini-tts`. |
| **Chrome, Edge or Firefox with a microphone** | Headphones are recommended so the tutor doesn't hear itself or a TV. |

### 1. Get the code

```bash
git clone https://github.com/pritambanerjee999/eureka.git
cd eureka
```

> If you received the project as a zip, unzip it and `cd` into the folder; the rest is identical.

### 2. Collect your credentials

**LiveKit** (3 values):
1. Open https://cloud.livekit.io and create (or open) a project.
2. Go to **Settings → API Keys** and create a key.
3. Copy the **WebSocket URL** (`wss://<project>.livekit.cloud`), the **API Key** and the **API Secret**.

**OpenAI** (1 value): create a secret key at https://platform.openai.com/api-keys.

**JWT secret** (1 value): any random string of 32+ characters. It signs login tokens. Generate one:

```bash
openssl rand -hex 32
# no openssl (e.g. Windows)? use Docker instead:
docker run --rm python:3.11-slim python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Create the `.env` file

All secrets and configuration are read from a single `.env` file in the project root.

```bash
cp .env.example .env          # Windows (cmd): copy .env.example .env
```

Open `.env` in any editor and replace the placeholder values on these five lines (their order in the file doesn't matter). Leave everything else as it is. The API refuses to start while `JWT_SECRET` is still the placeholder.

```dotenv
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=APIxxxxxxxxxxxx
LIVEKIT_API_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
JWT_SECRET=<the 64-character hex string from step 2>
```

<details>
<summary>All variables in <code>.env.example</code></summary>

| Variable | Required | Default | What it does |
|---|---|---|---|
| `LIVEKIT_URL` | yes | — | LiveKit Cloud WebSocket URL |
| `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` | yes | — | Signs room tokens and dispatches the agent |
| `OPENAI_API_KEY` | yes | — | Speech-to-text, the tutor model and the voice |
| `JWT_SECRET` | yes | — | Signs login tokens. The API won't start if it's under 32 characters or still the placeholder. |
| `REDIS_URL` | yes | `redis://redis:6379` | Compose service address. Leave as is. |
| `DATABASE_URL` | yes | `postgresql://eureka:eureka@postgres:5432/eureka` | Compose service address. Leave as is. If you change `POSTGRES_PASSWORD`, change the password here too. |
| `POSTGRES_PASSWORD` | yes | `eureka` | Password for the internal database (not exposed outside Docker). |
| `NEXT_PUBLIC_API_URL` | yes | `http://localhost:8000` | Where the browser finds the API. Built into the frontend, so rebuild after changing it. |
| `CORS_ORIGINS` | no | `http://localhost:3000` | Browser origins allowed to call the API |
| `TOKEN_RATE_LIMIT_PER_MINUTE` | no | `5` | Sessions a user can start per minute |
| `MAX_SESSION_SECONDS` | no | `1800` | Hard cap on a session's length |
| `USER_AWAY_SECONDS` | no | `180` | End a session after this long without the student speaking |
| `MAX_PAUSE_SECONDS` | no | `600` | End a session that stays paused this long |

</details>

### 4. Build and start the containers

```bash
docker compose up --build -d
```

The first build takes about 3–5 minutes on a cold Docker cache (it downloads the Python and Node dependencies); rebuilds are much faster. Five services start: `redis`, `postgres`, `api`, `agent` and `frontend`.

Check that everything is up:

```bash
docker compose ps
```

All five should be running (shown as `running` or `Up`, depending on your Docker version). Redis and Postgres also show `healthy`. Then confirm the voice agent has connected to LiveKit:

```bash
docker compose logs agent | grep "registered worker"
```

You should see a line like `registered worker ... "agent_name": "eureka-tutor"`. If it's not there after 30 seconds, see [Troubleshooting](#troubleshooting).

Optional: http://localhost:8000/docs shows the API's interactive docs, which confirms the API is up.

### 5. Use the app

1. Open **http://localhost:3000**. Use `localhost`, not your machine's IP address, because browsers only allow microphone access on `localhost` or HTTPS.
2. Click **Create an account**, choose a username (3–32 characters: lowercase letters, digits, `_` or `-`) and a password (8+ characters).
3. Pick any topic card, for example *Classical Mechanics → Why do things fall?*
4. When the browser asks, **allow the microphone**.
5. Within a few seconds Eureka greets you and introduces the topic. Answer out loud.

### 6. Stop, restart, reset

```bash
docker compose stop              # stop containers; data is kept
docker compose up -d             # start again
docker compose down              # remove containers; data is kept (Docker volumes)
docker compose down -v           # remove containers AND all data (users, history)
docker compose up --build -d     # rebuild after pulling new code or changing NEXT_PUBLIC_API_URL
```

---

## Test it

### Automated tests (no external services needed)

All external services (PostgreSQL, Redis, LiveKit, OpenAI) are mocked. Run the backend tests while the stack is up:

```bash
docker compose exec api   python -m pytest -q    # API: auth, ownership checks, token, history, schemas
docker compose exec agent python -m pytest -q    # Agent: tutor behaviour, guardrails, pause, conversation storage
docker compose --profile test run --rm frontend-test   # Frontend: Jest + React Testing Library
```

Expected results: **132 passed**, **94 passed** and **72 passed** (8 suites).

### Manual test script (about 5 minutes)

| # | Do this | Expect |
|---|---|---|
| 1 | Create an account and sign in | Landing page with level picker, topic grid, empty history sidebar, and a how-to-use footer |
| 2 | Click a topic and allow the mic | Session screen. Eureka speaks first: a hook, three directions, then a question. The transcript fills in live. |
| 3 | Answer, then ask a follow-up question | Eureka responds to what you said and checks your understanding with a question |
| 4 | Ask something off-subject ("who won the World Cup?") | A brief decline with a physics angle (e.g. how a ball curves). Questions about Eureka itself ("what are you?") are answered normally. |
| 5 | Click **Pause**, wait, then **Resume** | Eureka stops mid-sentence, the timer pauses, and on resume it welcomes you back with a one-line recap |
| 6 | Click **Mute** | Your mic is off (the button turns amber); unmute to continue |
| 7 | Type in **My Notes**, then **End Session** | Back on the landing page; the session is at the top of the sidebar under *Today* |
| 8 | Click that session in the sidebar | Transcript, checkpoints and your notes; **Continue this topic** starts a new session on it |
| 9 | Click **New session** in the sidebar | An open session ("ask me anything") starts |
| 10 | Click **Assess My Level** | Eureka asks three calibration questions, then tells you your level; the level picker preselects it next time |
| 11 | Log out and create a second account | The sidebar is empty. The second user can't see the first user's history (the API returns 403). |

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `docker compose` not found, or a `depends_on` error | You have Compose v1 (`docker-compose`). Install Docker Desktop or the Compose v2 plugin. |
| `port is already allocated` | Something else uses port 3000 or 8000. Stop it, or change the left side of the port mapping in `docker-compose.yml`. If you move the API off 8000, also update `NEXT_PUBLIC_API_URL` and `CORS_ORIGINS`, then rebuild. |
| `api` keeps restarting; logs mention `JWT_SECRET` | `JWT_SECRET` is missing, shorter than 32 characters, or still the `.env.example` placeholder. Fix `.env`, then `docker compose up -d`. |
| No `registered worker` line; agent logs show 401 or connection errors | Wrong `LIVEKIT_URL`, `LIVEKIT_API_KEY` or `LIVEKIT_API_SECRET`. The URL must start with `wss://`. Fix `.env`, then `docker compose up -d --force-recreate agent`. |
| Session screen opens but Eureka never speaks | Check `docker compose logs agent`. OpenAI `401`/`429` means a bad key or no billing/quota. Also check that the browser tab isn't muted and the mic is allowed. |
| Eureka keeps getting cut off or answers things you didn't say | The mic is picking up background audio (a TV, speakers). Use headphones. |
| "Failed to fetch" on the sign-in page | The API isn't reachable at `NEXT_PUBLIC_API_URL`. Check `docker compose ps` and http://localhost:8000/docs. |
| Database login errors after changing `POSTGRES_PASSWORD` | Postgres only sets the password when its volume is first created. Run `docker compose down -v` to reset, or keep the old password. |
| Two voices, or sessions handled by an old copy of the app | Run only one copy of the stack per LiveKit project. Every running copy registers an `eureka-tutor` worker, and LiveKit can send a session to any of them. Stop old clones with `docker compose down`. |
| See what a service is doing | `docker compose logs -f api` (or `agent`, `frontend`) |

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
  ├── GET /history, GET|PUT /notes  (Bearer JWT, own data only) ──► FastAPI ──► PostgreSQL
  │
  └── WebRTC audio ◄──────────────► LiveKit Cloud ◄────► Agent worker (agent)
                                                            ├── Silero VAD
                                                            ├── OpenAI Whisper (STT)
                                                            ├── GPT-4o (LLM + tools)
                                                            ├── OpenAI TTS
                                                            └── every turn ──► Redis conversation:{room}  (live state)
                                                                          └──► PostgreSQL conversations (history)
```

There are five Docker services: `redis`, `postgres`, `api`, `agent` and `frontend`. The browser calls the API to authenticate and get a room token, then talks to LiveKit Cloud directly over WebRTC. The agent worker joins the same room and runs the voice pipeline. Only the frontend (3000) and API (8000) are published; Redis and Postgres are reachable only inside the compose network.

**Separation of concerns**

| Concern | Where |
|---|---|
| Auth & users | `backend/api/routers/auth.py`, `services/auth_service.py`, `dependencies.py` |
| Session management | `backend/api/services/session_service.py` (Redis `session:{room}`), `routers/token.py` (token + dispatch) |
| Conversation handling | `backend/agent/services/conversation_service.py`: routes each turn to Redis and PostgreSQL, and restores a room's live context |
| Voice / AI layer | `backend/agent/main.py` (pipeline + events), `agent.py` (tutor behaviour, tools), `prompts.py`, `services/pause_service.py` |
| UI | `frontend/src/app/page.tsx`, `frontend/src/components/` |

**State**

| Store | Key / table | Holds | Lifetime |
|---|---|---|---|
| Redis | `session:{room}` (hash) | identity, topic, status. Written by the API, read by the agent on join. | 2 h TTL |
| Redis | `conversation:{room}` (list) | the live conversation for that room, one JSON turn per entry, capped at 200 | 24 h TTL |
| Redis | `user_room:{user}`, `ratelimit:token:{user}` | the user's one live room; the `/token` rate-limit counter | 2 h / 60 s |
| PostgreSQL | `users` | username, scrypt password hash | durable |
| PostgreSQL | `conversations` | every turn plus `session_start`, `checkpoint` and `level` records, keyed by user | durable |
| PostgreSQL | `notes` | the student's notes per session, keyed by (user, room) | durable |

**Project layout**

```
├── docker-compose.yml       # all five services (+ frontend-test profile)
├── .env.example             # every variable; copy to .env
├── backend/api/             # FastAPI: auth, tokens, sessions, history, notes  (+ tests/)
├── backend/agent/           # LiveKit agent worker: voice pipeline, tutor, tools (+ tests/)
└── frontend/                # Next.js 14 UI (src/app, src/components, src/__tests__)
```

---

## Product features (and why)

- **Accounts.** Username/password sign-up and login. History, notes and assessed level all belong to the account, so they follow you across browsers and devices.
- **Chat-style history sidebar.** Past sessions sit in a left sidebar grouped by *Today / Yesterday / Previous 7 days / Older*, like a chat app. Click one to reread the transcript, see what you understood and your notes, and **Continue this topic** with one click. History buried at the bottom of a page doesn't get used; a sidebar does. You can hide the sidebar for more room.
- **Level picker + spoken assessment.** Five levels (Spark → Singularity) tune the topic suggestions. **Assess My Level** runs a three-question spoken calibration. The agent saves the result with a tool call, and the UI preselects it next time.
- **Topic grid.** Five branches of physics with level-appropriate starter questions. Clicking one starts a session where Eureka speaks first: one vivid hook, three directions to explore, and a question about which one you want. The opening can't be interrupted by background noise. **New session** starts an open "ask me anything" session.
- **Understanding checkpoints.** When a student explains a concept in their own words, the agent calls `save_progress`, and the result shows up as a ✓ badge in history. This rewards understanding rather than time spent.
- **Mute and pause.** Mute the mic while you think, or pause the session. On pause, Eureka stops mid-sentence and waits without timing out. When you resume, it welcomes you back with a one-line recap. A pause ends the session after 10 minutes so an abandoned tab doesn't hold a room open.
- **Live session view.** Agent state visualizer (listening / thinking / speaking), live transcript, a notes pad that autosaves per session, and links to curated references (Feynman Lectures, HyperPhysics, PhET…).
- **Resilient sessions.** If an agent drops and is redispatched to the same room, it rebuilds its context from Redis and picks up where it left off instead of starting over.

---

## Key design decisions and tradeoffs

**Separate FastAPI service instead of Next.js route handlers.** This keeps LiveKit credentials and the JWT secret off the frontend, makes the session/auth layer independently testable and deployable, and gives a clean boundary between session management and the UI.

**STT → LLM → TTS pipeline instead of GPT-4o Realtime.** The pipeline adds latency (roughly 300–600 ms per turn) but gives independent control of each stage: swap voices, change STT settings or change models without touching the rest. It also produces text transcripts for free, which history and checkpoints depend on. For a tutor, the quality of the explanation matters more than shaving off the last few hundred milliseconds.

**Redis for live conversation state, PostgreSQL for durable history.** Redis holds what's hot and room-scoped: session metadata and the running conversation. Writes are O(1) (`RPUSH`), the list is capped (`LTRIM`), and it expires on its own. PostgreSQL holds what must outlive a session: users, per-user history and notes. Each turn is written to both concurrently, and a failure in one store is logged and never blocks the other. The cost is two writes per turn, which is cheap next to an STT/LLM/TTS round trip.

**Explicit, named agent dispatch.** In LiveKit, an unnamed worker is automatically dispatched to every new room. Combined with an explicit dispatch from `/token`, that put two agents (two overlapping voices) in each room. The worker now registers as `eureka-tutor`, which disables automatic dispatch, and `/token` dispatches exactly one agent by name.

**Auth: stateless JWT, stdlib scrypt, username as identity.** HS256 JWTs (7-day expiry) mean the API needs no session lookup per request and scales horizontally. Passwords are hashed with `hashlib.scrypt` (memory-hard, per-user salt), so there's no native dependency. The username doubles as the LiveKit participant identity, so the browser can never choose who it is. Login errors are identical for unknown users and wrong passwords, to avoid revealing which usernames exist. *Tradeoff:* the token is kept in `localStorage`, which is simpler but readable by an XSS bug. An httpOnly cookie plus CSRF protection would be the production choice.

**Per-user data isolation.** Every data endpoint checks ownership, and the checks are tested end to end against the running stack:
- `/history/{user}` and `/notes/{user}` return 403 unless `{user}` is the signed-in user. Forged or `alg=none` tokens get 401.
- Notes can only be saved against the caller's own sessions. The API checks the room's Redis session for a live room and the stored conversation for an old one; any other room returns 404.
- `/token` ignores any client-supplied identity or room name. It derives both from the JWT and a random room name.
- The agent writes checkpoints and levels to the identity the API stored for the room, not to whoever joined.
- Redis and Postgres have no published ports, so the stores can't be read around the API.

**Guardrails against misuse.** They're layered so no single check is load-bearing:

| Risk | Guardrail |
|---|---|
| Joining someone else's room | Room names are generated by the server only (`room-<128-bit hex>`); the client can't choose one. |
| Prompt injection through the topic | The API checks `topic` (≤80 chars, menu-title characters only, so no newlines or instruction-style punctuation), and the agent checks it again. Valid topics are quoted and explicitly labelled to the model as a subject name, not instructions. |
| Off-topic, harmful or jailbreak conversations | Physics tutor scope. Physics, questions about Eureka or the session, and short replies are answered normally. A clearly different subject (other school subjects, coding, trivia, opinions) is declined briefly with a physics angle, never with a "quick answer first" and never with the same line twice. A scope reminder is added to every turn's context so a long or manipulative conversation can't bury the rule. Background audio and garbled speech are not answered. Other prompt rules: conceptual explanations only for weapons or explosives; a supportive response and referral if a student mentions self-harm or danger; age-appropriate language and no collecting personal info; never reveal the prompt or switch persona. |
| Runaway OpenAI cost | Per-user `/token` rate limit (5/min, Redis). One live session per user: starting a new one closes the previous room and its agent. Sessions end after 3 minutes without the student speaking, after 10 minutes paused, and after 30 minutes at most. |
| Oversized or malformed input | Notes are a typed body capped at 20 000 chars, only for server-shaped room names. Tool arguments from the model are truncated. Login inputs are capped, so huge passwords can't be used to burn CPU. |
| Weak configuration | The API refuses to start without a `JWT_SECRET` of at least 32 chars. CORS allows only `CORS_ORIGINS` (no wildcard, no credentials). |

All limits are configurable in `.env` (see `.env.example`).

**Tools for state the UI needs.** Level and checkpoints are saved through LLM tool calls (`save_level`, `save_progress`) rather than by parsing transcripts, so the model decides when real understanding happened and the data arrives structured.

**No semantic cache.** Each tutoring reply depends on the whole conversation so far, so cache hits would be rare and a wrong hit would answer the wrong context. Most per-turn latency is speech synthesis, which a text cache doesn't remove. The one good candidate is the deterministic topic intro (same topic + level → same opening), where caching the text and audio would make the first words instant.

**Why Feynman-style physics.** Physics has a clear topic structure and benefits enormously from analogy and Socratic checking. A tutor that *checks understanding* instead of *delivering information* is a better product, and physics is where that gap is largest.

---

## Scaling to 10,000 concurrent sessions

| Layer | Today | At 10k sessions |
|---|---|---|
| **Agent workers** | 1 container | The bottleneck. Each session runs a live VAD/STT/LLM/TTS pipeline, so target roughly 25–50 sessions per 4-vCPU container. That means 200–400 containers, autoscaled on worker load. LiveKit Cloud already balances job dispatch across all registered `eureka-tutor` workers. |
| **API** | 1 Uvicorn process | Stateless: JWT auth, no in-process session state, and the `/token` rate limit already lives in Redis. Run multiple workers per pod behind a load balancer and scale horizontally. Move scrypt off the event loop and rate-limit `/auth/*` too. |
| **Redis** | Single node, new connection per call | Use a shared connection pool in both services; opening a connection per call is fine for a demo but too much churn at scale. Live data is small (10k rooms × 200 turns × ~300 B ≈ 600 MB), so one node with a replica works. Move to Redis Cluster sharded by room for headroom and failover. |
| **PostgreSQL** | Single instance, pool of 5 | Put PgBouncer in front, size the pools, and add a read replica for history and notes reads. Partition `conversations` by month (or by user hash). Batch turn inserts from the agent if write volume demands it. |
| **LiveKit** | LiveKit Cloud | Already distributed. If self-hosting, run LiveKit in cluster mode with a TURN fleet. |
| **OpenAI** | Per-turn API calls | Raise org rate limits, add retry with backoff, and consider cheaper or faster models (e.g. `gpt-4o-mini`, streaming TTS) for simple turns. Cost, not compute, becomes the main constraint. |

---

## Known limitations

- `/auth/login` and `/auth/register` have no rate limit yet, and scrypt runs on the API's event loop. Next step: hash in a thread pool and use a Redis limiter like the one `/token` has.
- Safety and scope rely on prompt rules plus a per-turn reminder. Production would add a moderation pass (e.g. OpenAI moderation on transcripts) to flag or end abusive sessions.
- History recorded before accounts existed (anonymous `user-xxxx` identities) isn't linked to any account. The `user-` username prefix is reserved so those records can't be claimed by accident.
- No password reset or email verification. Sessions last until the JWT expires (7 days) or the user logs out.

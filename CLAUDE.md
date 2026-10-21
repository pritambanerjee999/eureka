# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Eureka: a real-time voice physics tutor (Feynman-style) built on LiveKit. Take-home project; `PROMPT.md` is the assignment text and must stay verbatim. `README.md` and `workflow.md` are deliverables — when behaviour, env vars, endpoints or test counts change, update them (README quotes exact test pass counts, and `.env.example` must list every variable).

## Commands

Everything runs in Docker; there's no expectation of local Python/Node. All config comes from `.env` in the repo root (copy `.env.example`). The API refuses to start unless `JWT_SECRET` is ≥32 chars and not the `change-me…` placeholder.

```bash
docker compose up --build -d                 # build + start redis, postgres, api, agent, frontend
docker compose logs agent | grep "registered worker"   # confirm agent is registered with LiveKit
docker compose logs -f api                   # or agent / frontend

# Tests (all external services — Postgres, Redis, LiveKit, OpenAI — are mocked)
docker compose exec api   python -m pytest -q
docker compose exec agent python -m pytest -q
docker compose --profile test run --rm frontend-test        # Jest + RTL

# Single test
docker compose exec api python -m pytest -q tests/test_history_router.py::TestGetHistory::test_empty_history_returns_empty_list
docker compose exec agent python -m pytest -q -k pause
docker compose --profile test run --rm frontend-test npx jest src/__tests__/HistorySidebar.test.tsx
```

The base compose file doesn't mount source: after code changes, rebuild the affected service (`docker compose up --build -d <service>`). For hot reload, use the dev overlay, which mounts source, runs `uvicorn --reload`, restarts the agent via `watchfiles` (this ends any live voice session) and runs `next dev`. It also publishes Postgres on `127.0.0.1:5432` only:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d
```

Keep it a separate file, not `docker-compose.override.yml` (which Compose auto-loads), so reviewers' plain `docker compose up` stays production-like with no DB port. `NEXT_PUBLIC_API_URL` is baked into the production frontend build. Frontend lint: `npm run lint` in `frontend/`.

Python tests also run without Docker from a root venv (`python3 -m venv .venv && .venv/bin/pip install -r backend/api/requirements.txt -r backend/agent/requirements.txt`), from inside each service dir: `../../.venv/bin/python -m pytest -q`.

## Architecture

Three services plus Redis and Postgres (only ports 3000 and 8000 are published; Redis/Postgres are internal by design — don't add host ports).

- **`backend/api`** (FastAPI): auth (`/auth/*`, JWT HS256, stdlib scrypt), `/token` (issues LiveKit room token and explicitly dispatches the agent), history/notes/session-title endpoints, and `/study-plan/{identity}` (sends only session headers to `STUDY_PLAN_MODEL`; headers and suggestions are cached in Redis for 24 h). Routers in `routers/`, logic in `services/`, auth deps in `dependencies.py`.
- **`backend/agent`** (LiveKit Agents worker): `main.py` builds the STT (whisper-1) → LLM (gpt-4o) → TTS pipeline with Silero VAD, wires room/session events, and enforces session limits; `agent.py` is `PhysicsTutorAgent` (intro logic, `save_progress`/`save_level` tools, per-turn scope reminder); `prompts.py` holds the system prompt; `services/` handle Redis, Postgres, conversation persistence and pause.
- **`frontend`** (Next.js 14, Tailwind, `@livekit/components-react`): single page `src/app/page.tsx` + `src/components/`. JWT kept in `localStorage` (`src/lib/auth.ts`).

### Request flow / cross-service contracts

1. Browser logs in → JWT. The username is also the LiveKit participant identity; the client never chooses identity or room name.
2. `POST /token` generates `room-<uuid4>`, writes Redis hash `session:{room}` (identity, topic, status, and `source=plan` when the topic came from the study plan), enforces rate limit (`ratelimit:token:{user}`) and one live room per user (`user_room:{user}`, closing the previous room), then dispatches the agent **by name** (`AGENT_NAME`, default `eureka-tutor`). The worker is named so LiveKit's auto-dispatch is disabled — otherwise two agents join each room. `AGENT_NAME` must match in both services.
3. Agent joins, reads `session:{room}` for topic + identity, and restores any `conversation:{room}` turns (resume after worker restart → skips the intro).
4. Every turn (`conversation_item_added`) is written concurrently to Redis `conversation:{room}` (capped list, 24h TTL) and Postgres `conversations`; a failure in one store must not block the other. Postgres also holds `session_start`, `checkpoint` and `level` records in the same table, which the history UI uses to group sessions.
5. Pause/resume: the browser sets participant attribute `paused` = `"1"`/`"0"` (`SessionControls.tsx`); `PauseController` in the agent reacts. Sessions end on user-away timeout, max pause, or max duration.

### Things that are easy to break

- **Schema is defined twice**: `backend/api/services/db.py` and `backend/agent/services/db_service.py` both run `CREATE TABLE IF NOT EXISTS` for shared tables (`conversations`, `notes`). Keep them in sync; there are no migrations.
- **Topic validation is duplicated on purpose** (API `TokenRequest` schema and agent `safe_topic` regex) because the topic is interpolated into LLM instructions. Special topics: `__open__`, `__assess__`.
- **Ownership checks**: every data endpoint must call `require_identity` (403 for another user's identity) and, for room-scoped writes, verify the room belongs to the caller (`_owns_room` in `routers/history.py`: live Redis session or stored conversation; else 404). New endpoints should follow the same pattern.
- **Prompt caching**: keep the system prompt static — never put per-user or per-topic text in `PHYSICS_TUTOR_SYSTEM_PROMPT`; per-session context goes into `generate_reply` instructions / turn context.
- **LiveKit SDK version quirks**: event names and attributes matter (e.g. room is `session.room_io.room`, not `session.room`). A past bug came from listening to event names that don't exist in this SDK version — verify against the installed version.
- The agent must not call `logging.basicConfig` (LiveKit CLI configures logging; doing so duplicates lines).

## Testing conventions

- Both Python suites' `tests/conftest.py` set env vars and stub the `livekit` package via `sys.modules` **before** importing app code; modules are imported without a package prefix (the service dir is put on `sys.path`). `pytest.ini` uses `asyncio_mode = auto`.
- Mock all external services in tests (Redis, Postgres, LiveKit, OpenAI); tests must pass with no network.
- Running only one copy of the stack per LiveKit project matters for manual testing: every running copy registers an `eureka-tutor` worker and LiveKit may route sessions to any of them.

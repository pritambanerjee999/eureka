# Workflow

## AI Tools Used

### Claude Code (claude-sonnet-4-6) via the CLI
Primary tool for this entire project. Used it as an interactive pair programmer running directly in the terminal, not just for code generation but for architecture decisions and tradeoffs.

**How I used it:**
- Pasted the project prompt and asked it to design the full architecture before writing a single line of code. The planning agent (`subagent_type: Plan`) produced the directory tree, Redis key schema, LiveKit v1.0 API patterns, and scalability table that ended up in the README — in one shot.
- Once the plan was reviewed and approved, ran a single "implement it" prompt. Claude wrote all ~36 source files in parallel (multiple `Write` tool calls at once), which meant the skeleton was complete in under 5 minutes.
- Used it for live debugging — pasted Docker build errors back into the conversation and had it diff and fix specific files rather than regenerating everything.

**Specific models / harnesses:**
- Model: `claude-sonnet-4-6` (Sonnet 4.6)
- Harness: Claude Code CLI (`claude` command), running in the `/Users/pritam/projects` working directory
- Used the built-in `Plan` subagent for upfront architecture design and `Write`/`Edit` tools for file creation and patching

### Why this workflow is fast
The key leverage is *planning before coding*. By spending 2 minutes getting a complete architecture spec out of the planning agent first, every subsequent code-generation call had enough context to produce something that actually fits together. No back-and-forth on "wait, where does this import from?" because the file tree and separation of concerns were locked before any file was created.

The parallel `Write` tool calls matter too — when Claude can write 10 files simultaneously rather than sequentially, the wall-clock time for a full project scaffold drops from minutes to seconds.

### Claude Code (claude-opus-5-5) — accounts, history UI, and bug hunting
A later session in the same Claude Code CLI harness, on Opus 5.5 (`claude-opus-5-5`), handled user management, the history sidebar, and several bugs found along the way.

**How I used it:**
- **Persistent memory for continuity.** Claude Code's file-based memory (`~/.claude/projects/.../memory/`) held a project summary (stack, LiveKit gotchas, test commands) and my standing feedback ("always rebuild + restart Docker after a change", "mock every external service in tests"). Each new session started with the right context and conventions instead of rediscovering them.
- **Steering mid-task.** I sent new requirements while it was still working ("put history in a sidebar like a chat app"; a screenshot of overlapping voices). It folded them into the running task instead of restarting.
- **Debugging from evidence, not guesses.** For the "multiple voices" bug it read the agent and API logs, saw two dispatch IDs per room against a single `/token` call, and traced it to LiveKit auto-dispatching unnamed workers. The fix was naming the worker and dispatching explicitly, plus a regression test.
- **Auditing against the brief.** When I asked it to update the docs against `PROMPT.md`, it first checked the code against each requirement. It found that conversations weren't actually going to Redis, queried Postgres, and saw that zero spoken turns had ever been saved. Introspecting the installed `livekit-agents` SDK showed the event names in `main.py` didn't exist in v1.8.6. It flagged the gap and asked before changing scope, then fixed both issues together.
- **Verifying for real.** Beyond unit tests, it registered a user against the live API, joined the room with a headless LiveKit client, and confirmed the agent's greeting landed in both Redis (`conversation:{room}`, 24 h TTL) and Postgres.
- **Tests as part of every change.** Auth service, auth router, ownership checks, conversation routing, agent resume path, and the new React components each got tests with mocked dependencies. It also found a Jest config typo (`setupFilesAfterFramework`) that had kept the frontend suite from ever running.

**Specific models / harnesses:**
- Model: `claude-opus-5-5` (Opus 5.5)
- Harness: Claude Code CLI with persistent memory, Bash/Read/Edit/Write tools, and `AskUserQuestion` for scope decisions
- Docker Compose for every build, test run and restart; `curl` and a headless `livekit.rtc` client for end-to-end checks

## Manual Work
- Reviewed the architecture plan and approved the tech stack choices before implementation started
- Verified the LiveKit Agents v1.0 API patterns matched what the `livekit-agents` package actually exports
- Wrote the `PROMPT.md` content (copied verbatim from the assignment)
- Decided product direction (accounts, chat-style history sidebar) and approved the scope change to route conversations through Redis
- Tested the voice experience by hand in the browser and reported bugs with screenshots
- Will record the video walkthrough manually

## Not Used
- Cursor / Copilot — already have Claude Code in the terminal, no need for a separate IDE plugin
- ChatGPT — same
- GitHub Copilot — same

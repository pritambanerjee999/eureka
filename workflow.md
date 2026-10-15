# Workflow

## AI Tools Used

Claude Code (the CLI) was the only AI coding tool used. The work happened in two phases: Sonnet 4.6 for the initial build, then Opus 5.5 for accounts, bug fixing, guardrails, testing and release (the sections below).

### Claude Code (claude-sonnet-4-6): initial architecture and build
Used as an interactive pair programmer running directly in the terminal, for architecture decisions and tradeoffs as well as code generation.

**How I used it:**
- Pasted the project prompt and asked it to design the full architecture before writing a single line of code. The planning agent (`subagent_type: Plan`) produced the directory tree, Redis key schema, LiveKit Agents 1.x API patterns (the project runs `livekit-agents` 1.8.6), and the first version of the scalability table in the README, in one shot.
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

### Claude Code (claude-opus-5-5): review, guardrails, polish and release
The same Opus 5.5 session then took the project from "works on my machine" to something a reviewer can clone and run.

**How I used it:**
- **Code review, then a scoped fix.** I asked for a thorough review focused on guardrails and misuse. It returned findings ranked by severity, and I chose the scope ("security + guardrails only"). Fixes:
  - server-generated room names (the client could previously join any room);
  - topic validation against prompt injection;
  - per-user rate limits and one live session per user;
  - idle and maximum session timeouts;
  - size-capped inputs;
  - a required strong `JWT_SECRET` and locked-down CORS.

  The remaining findings went into the README as known limitations.
- **Live attack checks, not just unit tests.** After each security change it attacked the running stack:
  - a second account tried to read or write the first one's history and notes, including uppercase and URL-encoded usernames;
  - it sent tokens with a forged `sub` and `alg=none`;
  - it tried to hijack a room through the `/token` body;
  - it called `/token` repeatedly until the rate limit kicked in.

  That's how it caught the worst bug of the project: Postgres and Redis were published on all interfaces, so anyone on the network could read every user's data without going through the API. It confirmed the exposure from the LAN IP, removed the host port mappings, and deleted the throwaway accounts afterwards.
- **Diagnosing bugs from logs and stored data.** When I reported "I clicked a topic and it never started teaching", it read the agent logs and the Redis transcript for that room. My microphone had picked up a TV, and voice-activity detection kept interrupting the intro. The fix was to make the opening non-interruptible (verified against the installed SDK's `generate_reply` signature first).
- **Testing prompts against the real model.** Prompt changes were checked by sending scripted conversations to GPT-4o with the production system prompt, not just by asserting on prompt text. That loop caught an over-correction. My "physics only" request first produced a rule so strict that it refused questions about the tutor itself and replies like "yeah". I sent screenshots, and it rewrote the rule to list what *is* in scope, replayed my exact failing conversation to confirm the fix, and saved the lesson to memory ("guardrails must not over-refuse").
- **Mid-task feature requests.** While it was working I sent mute/pause, a collapsible sidebar, a footer-style how-to guide, and "does it use a semantic cache?". Each was built, tested, deployed and committed as its own change. Pause is a participant attribute that the agent watches; that logic lives in a small, unit-tested `PauseController`. The cache question got a reasoned "no" that is now in the README.
- **Git and GitHub.**
  - Branch-per-feature, with a commit per change and attribution in each message.
  - When the push failed it diagnosed the missing SSH key and walked me through adding one.
  - It wrote the PR description, and after the merge it noticed the PR had closed before the last two commits and merged those into `main` too.
- **A second agent as an independent tester.** Its own testing was biased by knowing the code. So it spawned a separate general-purpose subagent with only the README and the repo URL. The subagent cloned from GitHub into a scratch folder, built the stack under its own compose project name (to protect my data), and ran all three test suites. It then drove my installed Chrome through Playwright with a fake microphone: sign up, start a topic, hear the intro, pause and resume, end the session, and check that a second user gets 403. It came back with screenshots and six README gaps, plus a real config issue: the `.env.example` placeholder JWT secret passed validation. All of these were fixed.

- **Auditing the docs against the code and the brief.** As a final pass it went through `PROMPT.md` requirement by requirement and checked each factual claim in the markdown against the source. That meant diffing every setting the code reads against `.env.example`, and checking TTLs, limits, pool sizes and topic counts. It caught and fixed four things:
  - two variables missing from `.env.example`;
  - "five" physics branches where there are six;
  - room-name entropy overstated: a UUID4 has 122 random bits, not 128;
  - a Redis set the docs said was cleaned up when nothing ever removes from it, now listed as a known limitation instead.

  It also confirmed that `PROMPT.md` is byte-identical to the original commit.
- **Thinking through scaling with it.** I asked how we'd cache FAQs, whether semantic caching makes sense, whether RAG on the topic would help, and what else matters at 10k sessions. It reasoned from this specific product, not a generic checklist:
  - **Measured before claiming.** It counted the system prompt (~1,150 tokens, over OpenAI's 1,024-token threshold) before saying prompt caching already applies. It also checked that the per-turn reminder is appended at the end, so it doesn't break the cached prefix.
  - **Ordered caching by safety.** In tutoring a wrong cached answer is worse than a miss, so the plan runs from exact and safe to fuzzy and guarded:
    1. provider prompt caching;
    2. intro text and audio keyed by topic and level;
    3. pre-rendered fixed phrases;
    4. reviewed FAQ answers;
    5. a semantic cache, namespaced by topic, level and prompt version, used only for standalone questions, and calibrated on wrong-hit rate before launch.
  - **RAG: not per turn.** It argued against per-turn RAG for general physics (the model already knows it, and retrieval adds latency to every voice reply). It named where RAG does pay off: curriculum alignment, a misconception and analogy bank, grounded facts and citations, and the student's own history. Its design retrieves once at session start, otherwise only through a tool call, and shares one vector index with the semantic cache.
  - **Added the rest.** Observability, model routing, admission control, async persistence, graceful drain, multi-region, lifecycle webhooks and data retention.

  It wrote all of this into the README's design decisions and scaling sections, kept consistent with the existing "no semantic cache in this version" decision.

**Specific models / harnesses:**
- Model: `claude-opus-5-5` (Opus 5.5) for the main session and the tester subagent
- Harness: Claude Code CLI, the `Agent` tool (general-purpose subagent), persistent memory
- Tools driven through Claude Code: Docker Compose, `git` over SSH, the GitHub REST API (PR status), the OpenAI API (prompt evaluation), Playwright with headless Chrome (browser end-to-end test)

## Manual Work
- Reviewed the architecture plan and approved the tech stack choices before implementation started
- Verified the LiveKit Agents 1.x API patterns matched what the `livekit-agents` package actually exports
- Wrote the `PROMPT.md` content (copied verbatim from the assignment)
- Made the product decisions: accounts, chat-style history sidebar, mute/pause, footer guide, physics-only scope, and the change to route conversations through Redis
- Chose the review scope (security and guardrails first) and approved each risky step: pushing, merging
- Tested the voice experience by hand in the browser and reported bugs with screenshots: overlapping voices, a dead "New session" button, an intro cut off by TV audio, and over-refusal
- Created the GitHub repo, added the SSH key, and merged the PR
- Will record the video walkthrough manually

## Not Used
- Cursor / GitHub Copilot: Claude Code in the terminal already covers editing, and it can also run Docker, tests and git, which an IDE plugin can't
- ChatGPT: same reason; OpenAI models are used only inside the product (STT, tutor LLM, TTS) and for evaluating prompts

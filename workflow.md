# Workflow

## Tools and models

| Tool | Model | Used for |
|---|---|---|
| Claude Code (terminal CLI) | Sonnet 4.6 (`claude-sonnet-4-6`) | Planning the architecture and building the first version |
| Claude Code (terminal CLI) | Opus 5.5 (`claude-opus-5-5`) | Accounts, history UI, bug fixes, security, tests, docs and release |

Claude Code was my only AI coding tool. It runs in the terminal, so besides writing code it could run Docker, tests, git and scripts against the live app.

## How I worked

**1. Plan first, then build.** I gave Sonnet the assignment and asked for a full design before any code: folder layout, Redis keys, LiveKit API usage, and a scaling plan. I reviewed it, then asked it to implement. It wrote about 36 files in one go, and I pasted Docker errors back to it until everything ran.

**2. Build features in small steps.** With Opus I added accounts, a chat-style history sidebar, mute and pause, and a how-to guide. Later I added renaming sessions in the sidebar, because several sessions on the same topic all had the same name. It went in as a small, complete change: a database table, an endpoint with the same ownership check as notes, inline editing in the sidebar, and tests. It also checked the rename against the live API, including blocking another user. I often sent the next request, or a screenshot of a bug, while it was still working, and it folded that in. Every change came with tests and a Docker rebuild before it called the change done.

**3. Debug from evidence.** I reported bugs as I saw them, and it checked logs and stored data before changing code:
- *Two voices talking at once.* The logs showed two agents per room. LiveKit was auto-sending an unnamed worker on top of ours. Fix: name the worker.
- *Conversations never saved.* The code listened for event names that don't exist in this SDK version.
- *Tutor never started teaching.* My mic was picking up a TV, which kept cutting off the intro. Fix: the intro can't be interrupted.
- *Tutor refused everything.* My "physics only" rule was too strict and it refused questions like "what are you?". It replayed my exact conversation against GPT-4o until the rule worked.

**4. Review for security.** I asked for a code review focused on misuse and chose to fix security and guardrails first. It then tested the running app like an attacker: another user's data, forged logins, joining someone else's room. That found the worst bug: the database and Redis were open to my local network. Fixed and re-tested.

**5. Test like a stranger.** To check the README really works, it started a second, separate agent that knew only the README and the GitHub link. That agent cloned the repo, ran everything in Docker, ran the tests, and used Chrome to sign up, talk to the tutor, and confirm users can't see each other's data. It reported a few unclear README steps and one config issue, which we fixed.

**6. Check the docs against the code.** Before submitting, it checked every line of the README and `.env.example` against the code and this assignment, and fixed what was wrong. That included a missing variable, a wrong topic count, and a cleanup claim that wasn't true.

**7. Think through scaling.** I asked about caching FAQs, semantic caching and RAG. It checked facts first (for example, that our prompt is long enough for OpenAI's automatic caching) and suggested only what fits a voice tutor. The plan, now in the README, is:
- start with exact, safe caches;
- add a guarded semantic cache later;
- use RAG only at session start or when the model asks for a fact, not on every turn.

## What helped most
- **Memory between sessions.** Claude Code kept a project summary and my rules ("always rebuild Docker after a change", "mock external services in tests"), so each session started with the right context.
- **Testing the real app, not just unit tests.** The biggest bugs (open database ports, the TV interruption, over-refusal) only showed up on the running system.
- **A fresh agent as a tester.** It had no knowledge of the code, so it caught gaps I'd have missed.

## What I did myself
- Approved the design and made the product decisions: accounts, history sidebar, session renaming, mute and pause, physics-only scope.
- Tested the voice tutor by hand and reported bugs with screenshots.
- Chose what to fix first and approved pushes and merges.
- Set up the GitHub repo and SSH key, and merged the PR.
- Copied `PROMPT.md` from the assignment and recorded the video walkthrough.

## Not used
Cursor, GitHub Copilot and ChatGPT. Claude Code covered everything, including running the app. OpenAI models are used only inside the product (speech-to-text, the tutor, the voice) and to test prompts.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Daily Botman News is a Python 3.13 worker that fetches AI-related posts from X (Twitter), filters them through Google Gemini for relevance, and publishes curated results to a Redis stream and Discord forum threads. It runs on a 30-minute cycle via APScheduler.

## Running the Project

```bash
# Production (Docker)
cp .env.example .env   # fill in API keys
docker compose up       # starts Redis + botman

# Local development
pip install -r requirements.txt
python -m app.main
```

There are no tests or linting configured.

## Architecture

The pipeline runs every 30 minutes and flows through discrete stages, each in its own module:

```
fetcher.py -> pipeline.py -> scorer.py -> store.py -> discord.py
  (X API)    (orchestrator)   (Gemini)    (Redis)    (Discord)
```

**pipeline.py** is the orchestrator. It calls each stage in sequence: fetch -> dedup (via store) -> engagement gate -> score (via Gemini) -> select top N -> store -> publish to Discord. All error handling and early-exit logic lives here.

**main.py** is the entry point. It configures APScheduler with two jobs: the pipeline (every N minutes) and cleanup (midnight ART). Handles SIGTERM/SIGINT for graceful shutdown.

**config.py** holds a frozen `Settings` dataclass populated from env vars. The `ALIGNMENTS` system prompt for Gemini is hardcoded here with detailed relevance criteria (high/medium/low interest categories). Access settings via `from app.config import settings`.

**store.py** manages Redis state. All keys are date-scoped (`known:{date}`, `published:{date}`, `post:{date}:{id}`) and cleaned up daily. The `stream:noticias` stream is persistent and capped at 1000 entries.

**cleanup.py** runs at midnight ART: deletes yesterday's Discord threads and clears yesterday's Redis keys.

## Key Design Decisions

- **Date-scoped Redis keys**: All transient state uses `{YYYY-MM-DD}` scoping so cleanup is a simple key deletion, not TTL management.
- **Engagement gate before Gemini**: Posts below `MIN_ENGAGEMENT` are dropped before calling the Gemini API to save tokens.
- **Gemini returns structured JSON**: The scorer expects a JSON array with index, pass/fail, priority, tags, title, reason, and tldr fields.
- **All HTTP calls use httpx** (synchronous): The project doesn't use async/await despite httpx supporting it.
- **Timezone**: All scheduling uses `America/Argentina/Buenos_Aires` (ART).

## External Services

| Service | Module | Auth |
|---------|--------|------|
| X API v2 | fetcher.py | Bearer token (`X_BEARER_TOKEN`) |
| Google Gemini | scorer.py | API key (`GEMINI_API_KEY`) |
| Redis | store.py | URL (`REDIS_URL`) |
| Discord API v10 | discord.py | Bot token (`DISCORD_BOT_TOKEN`) |

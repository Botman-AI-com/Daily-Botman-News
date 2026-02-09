# Daily Botman News

A worker that fetches posts from X, filters them through Gemini for relevance, and publishes the best ones to a Redis stream and Discord.

## How it works

```
X API  -->  Gemini filter  -->  Redis stream
 (fetch)     (score/filter)      + Discord thread
```

Every 30 minutes the pipeline runs:

1. **Fetch** — pulls up to `MAX_RESULTS` tweets from X sorted by relevancy, scoped to today
2. **Dedup** — skips posts already seen this cycle via date-scoped Redis sets
3. **Engagement gate** — drops tweets below `MIN_ENGAGEMENT` (likes + retweets + quotes) to avoid wasting Gemini tokens on noise
4. **Gemini filter** — sends surviving posts with an alignments prompt as system instruction; Gemini returns only relevant posts tagged with priority (high/medium)
5. **Publish** — stores the top `TOP_N` post(s) in Redis and creates a Discord forum thread

At midnight ART a cleanup job deletes yesterday's transient keys.

## Data model

All keys are date-scoped and ephemeral except the stream:

| Key | Type | Purpose |
|-----|------|---------|
| `known:{date}` | SET | Tweet IDs seen today (dedup across cycles) |
| `published:{date}` | SET | Tweet IDs published today (prevents re-publish) |
| `post:{date}:{id}` | HASH | Post metadata |
| `stream:noticias` | STREAM | Persistent output (capped at 1000 entries) |

## Setup

```
cp .env.example .env
# fill in X_BEARER_TOKEN, GEMINI_API_KEY, DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID
docker compose up
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `X_BEARER_TOKEN` | — | X API bearer token |
| `GEMINI_API_KEY` | — | Google Gemini API key |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model ID |
| `ALIGNMENTS` | (hardcoded) | System prompt for the relevance filter |
| `X_SEARCH_QUERY` | AI-focused query | X search query |
| `MAX_RESULTS` | `30` | Tweets fetched per cycle |
| `TOP_N` | `1` | Posts published per cycle |
| `FETCH_INTERVAL_MINUTES` | `30` | Pipeline interval |
| `MIN_AGE_MINUTES` | `30` | Minimum tweet age before fetching |
| `MIN_ENGAGEMENT` | `3` | Min likes+retweets+quotes to reach Gemini |
| `DISCORD_BOT_TOKEN` | — | Discord bot token |
| `DISCORD_CHANNEL_ID` | — | Discord forum channel for news threads |

## Project structure

```
app/
  main.py       # Scheduler entry point
  config.py     # Settings from env vars
  fetcher.py    # X API search
  scorer.py     # Gemini relevance filter
  store.py      # Redis storage + stream
  discord.py    # Discord forum thread publisher
  pipeline.py   # Orchestrates fetch -> filter -> publish
  cleanup.py    # Midnight key expiry
```

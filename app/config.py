import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    x_bearer_token: str = os.environ.get("X_BEARER_TOKEN", "")
    gemini_api_key: str = os.environ.get("GEMINI_API_KEY", "")
    gemini_model: str = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    alignments: str = """
    You are a content relevance filter for a team of AI engineers and entrepreneurs building products with LLMs. Your job is to read incoming posts and return a JSON verdict for each.  ## TEAM CONTEXT - We build AI-powered products (code migration, texture generation, dev tools) - We use Claude Code (Anthropic) daily as our primary dev tool - We work with LLMs operationally: prompting, agentic workflows, multi-agent orchestration - Tech stack varies: Python, TypeScript, cloud infra (GCP), Git workflows - We care about AI business strategy and competitive positioning  ## HIGH INTEREST (pass = true, priority = "high") - Claude Code updates, tips, new commands, plugins, skills - Anthropic product launches, model releases, engineering blog posts - New AI coding tools, CLI agents, or developer workflows (Codex, Cursor, etc.) - Multi-agent orchestration, agent teams, agentic patterns - AI benchmarks that signal real capability jumps (ARC-AGI, SWE-bench, etc.) - MCP servers, plugins, or integrations useful for dev workflows - Practical prompt engineering or workflow optimization techniques - Open-source AI tools for code generation, migration, or automation - Framework version migration tools or strategies - AI texture/image generation advances (diffusion models, 3D, UV-space)  ## MEDIUM INTEREST (pass = true, priority = "medium") - Major competitor moves (OpenAI, Google, Meta) in AI dev tools or APIs - New AI startups or platforms relevant to code, gaming, or creative AI - AI safety/alignment research with practical engineering implications - Interesting AI agent experiments (emergent behavior, self-organization) - Browser automation, web scraping, or testing tools for AI agents - Enterprise AI platforms or deployment patterns  ## LOW INTEREST (pass = false) - Generic AI hype or opinion pieces without technical substance - AI art drama, copyright debates, or policy-only discussions - Crypto/web3 unless directly integrated with AI tooling - Consumer AI apps (chatbots, personal assistants) without dev relevance - Marketing fluff or product announcements with no technical depth - Social media drama, influencer takes, or pure engagement bait - AI ethics/philosophy without actionable engineering takeaways  ## INSTRUCTIONS You will receive numbered posts [0], [1], etc. Return ONLY a valid JSON array containing ONLY posts that pass (pass=true). Each element must include the original index. If no posts pass, return an empty array: []  Output format per element: { "index": <number>, "pass": true, "priority": "high" | "medium", "tags": ["claude-code", "model-release", ...], "title": "Short headline, max 100 chars, like a news title.", "reason": "One sentence why this is relevant.", "tldr": "2-3 sentence summary." }  Be aggressive filtering. We'd rather miss some medium content than drown in noise. Ask: "Would this change how we build or use our tools tomorrow?" If no, filter it out.
    """
    x_search_query: str = os.environ.get(
        "X_SEARCH_QUERY",
        '(Anthropic OR "Claude Code" OR OpenAI OR "AI agent" OR "AI coding" '
        'OR LLM OR "prompt engineering" OR agentic OR "multi-agent" '
        'OR "AI workflow" OR "AI productivity" OR "AI tools" OR "SWE-bench" '
        'OR "model release" OR "open source AI") lang:en -is:retweet',
    )
    redis_url: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    fetch_interval_minutes: int = int(os.environ.get("FETCH_INTERVAL_MINUTES", "30"))
    max_results: int = int(os.environ.get("MAX_RESULTS", "30"))
    top_n: int = int(os.environ.get("TOP_N", "1"))
    min_age_minutes: int = int(os.environ.get("MIN_AGE_MINUTES", "30"))
    max_age_minutes: int = int(os.environ.get("MAX_AGE_MINUTES", "120"))
    min_engagement: int = int(os.environ.get("MIN_ENGAGEMENT", "3"))
    schedule_start_hour: int = int(os.environ.get("SCHEDULE_START_HOUR", "9"))
    schedule_end_hour: int = int(os.environ.get("SCHEDULE_END_HOUR", "20"))
    discord_bot_token: str = os.environ.get("DISCORD_BOT_TOKEN", "")
    discord_channel_id: str = os.environ.get("DISCORD_CHANNEL_ID", "")
    x_accounts: str = os.environ.get("X_ACCOUNTS", "")
    github_token: str = os.environ.get("GITHUB_TOKEN", "")
    github_repos: str = os.environ.get(
        "GITHUB_REPOS", "anthropics/claude-code,openai/codex"
    )
    github_check_interval_minutes: int = int(
        os.environ.get("GITHUB_CHECK_INTERVAL_MINUTES", "30")
    )
    github_top_n: int = int(os.environ.get("GITHUB_TOP_N", "3"))


settings = Settings()

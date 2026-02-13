import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

SEARCH_URL = "https://api.x.com/2/tweets/search/recent"
MAX_QUERY_LEN = 512


def _build_account_queries() -> list[str]:
    """Split X_ACCOUNTS into batched queries under 512 chars."""
    raw = settings.x_accounts
    if not raw:
        return []

    accounts = [a.strip() for a in raw.split(",") if a.strip()]
    if not accounts:
        return []

    suffix = " -is:retweet"
    # 2 for parens, len(suffix), small buffer
    budget = MAX_QUERY_LEN - len(suffix) - 2

    queries: list[str] = []
    batch: list[str] = []
    length = 0

    for acct in accounts:
        part = f"from:{acct}"
        sep = len(" OR ") if batch else 0
        needed = len(part) + sep

        if length + needed > budget and batch:
            q = (
                "("
                + " OR ".join(f"from:{a}" for a in batch)
                + ")"
                + suffix
            )
            queries.append(q)
            batch = [acct]
            length = len(part)
        else:
            batch.append(acct)
            length += needed

    if batch:
        q = (
            "("
            + " OR ".join(f"from:{a}" for a in batch)
            + ")"
            + suffix
        )
        queries.append(q)

    return queries


def fetch_recent_posts() -> list[dict]:
    """Fetch recent posts from X.

    If X_ACCOUNTS is set, fetches from those accounts in batched
    queries. Otherwise falls back to X_SEARCH_QUERY keyword search.
    """
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(minutes=settings.max_age_minutes)
    end_time = now - timedelta(minutes=settings.min_age_minutes)

    if end_time <= start_time:
        logger.info("No valid time window — min_age >= max_age.")
        return []

    account_queries = _build_account_queries()
    queries = account_queries or [settings.x_search_query]

    headers = {
        "Authorization": f"Bearer {settings.x_bearer_token}",
    }
    base_params = {
        "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end_time": end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "max_results": settings.max_results,
        "tweet.fields": "created_at,public_metrics,author_id",
        "sort_order": "relevancy",
    }

    all_posts: list[dict] = []
    for query in queries:
        params = {**base_params, "query": query}
        resp = httpx.get(
            SEARCH_URL, params=params,
            headers=headers, timeout=30,
        )
        resp.raise_for_status()
        posts = resp.json().get("data", [])
        all_posts.extend(posts)
        logger.info(
            "Fetched %d posts from X API (query %d/%d).",
            len(posts),
            queries.index(query) + 1,
            len(queries),
        )

    # Deduplicate by tweet ID across batches
    seen: set[str] = set()
    unique: list[dict] = []
    for p in all_posts:
        if p["id"] not in seen:
            seen.add(p["id"])
            unique.append(p)

    logger.info(
        "Total unique posts fetched: %d.", len(unique),
    )
    return unique

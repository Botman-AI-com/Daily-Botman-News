import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

SEARCH_URL = "https://api.x.com/2/tweets/search/recent"


def fetch_recent_posts() -> list[dict]:
    """Fetch today's posts from X that are older than MIN_AGE_MINUTES.

    Returns a list of tweet dicts with id, text, created_at, and public_metrics.
    """
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(minutes=settings.max_age_minutes)
    end_time = now - timedelta(minutes=settings.min_age_minutes)

    if end_time <= start_time:
        logger.info("No valid time window — min_age >= max_age.")
        return []

    params = {
        "query": settings.x_search_query,
        "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end_time": end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "max_results": settings.max_results,
        "tweet.fields": "created_at,public_metrics,author_id",
        "sort_order": "relevancy",
    }
    headers = {"Authorization": f"Bearer {settings.x_bearer_token}"}

    resp = httpx.get(SEARCH_URL, params=params, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    posts = data.get("data", [])
    logger.info("Fetched %d posts from X API.", len(posts))
    return posts

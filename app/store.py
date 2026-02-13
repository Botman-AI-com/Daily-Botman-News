import logging
from datetime import datetime, timezone

import redis

from app.config import settings

logger = logging.getLogger(__name__)

r = redis.from_url(settings.redis_url, decode_responses=True)

STREAM_KEY = "stream:noticias"


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def is_known(tweet_id: str) -> bool:
    return r.sismember(f"known:{_today()}", tweet_id)


def mark_known(tweet_ids: list[str]) -> None:
    if tweet_ids:
        r.sadd(f"known:{_today()}", *tweet_ids)


def save_post(post: dict) -> bool:
    """Save post hash to Redis. Returns True if the post has NOT been published yet."""
    date = _today()
    tweet_id = post["id"]
    key = f"post:{date}:{tweet_id}"
    link = f"https://x.com/i/status/{tweet_id}"

    r.hset(key, mapping={
        "link": link,
        "short_title": post.get("short_title", ""),
        "published": "0",
        "discord_thread_id": post.get("discord_thread_id", ""),
    })
    mark_known([tweet_id])

    return not r.sismember(f"published:{date}", tweet_id)


def save_thread_id(tweet_id: str, thread_id: str) -> None:
    """Persist the Discord thread ID on an existing post hash."""
    r.hset(f"post:{_today()}:{tweet_id}", "discord_thread_id", thread_id)


def publish_to_stream(post: dict) -> None:
    """Push a post to the presentation stream. Idempotent via published set."""
    date = _today()
    tweet_id = post["id"]

    if r.sismember(f"published:{date}", tweet_id):
        return

    link = f"https://x.com/i/status/{tweet_id}"
    now = datetime.now(timezone.utc).isoformat()

    r.xadd(STREAM_KEY, {
        "tweet_id": tweet_id,
        "link": link,
        "short_title": post.get("short_title", ""),
        "published_at": now,
    }, maxlen=1000)

    r.sadd(f"published:{date}", tweet_id)
    r.hset(f"post:{date}:{tweet_id}", "published", "1")

    logger.info(
        "Published to stream: [%s] %s",
        tweet_id, post.get("short_title", ""),
    )


# --------------- GitHub helpers ---------------

def is_gh_known(item_id: str) -> bool:
    return r.sismember(f"gh_known:{_today()}", item_id)


def mark_gh_known(item_ids: list[str]) -> None:
    if item_ids:
        r.sadd(f"gh_known:{_today()}", *item_ids)


def save_gh_post(post: dict) -> bool:
    """Save GitHub post hash. Returns True if NOT yet published."""
    date = _today()
    item_id = post["id"]
    key = f"gh_post:{date}:{item_id}"

    r.hset(key, mapping={
        "url": post.get("url", ""),
        "short_title": post.get("short_title", ""),
        "published": "0",
        "discord_thread_id": post.get("discord_thread_id", ""),
    })
    mark_gh_known([item_id])

    return not r.sismember(f"gh_published:{date}", item_id)


def save_gh_thread_id(item_id: str, thread_id: str) -> None:
    """Persist Discord thread ID on a GitHub post hash."""
    key = f"gh_post:{_today()}:{item_id}"
    r.hset(key, "discord_thread_id", thread_id)


def publish_gh_to_stream(post: dict) -> None:
    """Push a GitHub item to the stream. Idempotent."""
    date = _today()
    item_id = post["id"]

    if r.sismember(f"gh_published:{date}", item_id):
        return

    now = datetime.now(timezone.utc).isoformat()

    r.xadd(STREAM_KEY, {
        "item_id": item_id,
        "url": post.get("url", ""),
        "short_title": post.get("short_title", ""),
        "source": "github",
        "published_at": now,
    }, maxlen=1000)

    r.sadd(f"gh_published:{date}", item_id)
    r.hset(f"gh_post:{date}:{item_id}", "published", "1")

    logger.info(
        "Published GH to stream: [%s] %s",
        item_id, post.get("short_title", ""),
    )

import logging
from datetime import datetime, timedelta, timezone

import redis

from app.config import settings
from app import discord

logger = logging.getLogger(__name__)

r = redis.from_url(settings.redis_url, decode_responses=True)


def midnight_cleanup() -> None:
    """Delete yesterday's Discord threads and Redis keys. Runs at 00:00 ART."""
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

    # 1. Delete Discord threads created yesterday
    thread_ids = []
    cursor = 0
    while True:
        cursor, keys = r.scan(cursor, match=f"post:{yesterday}:*", count=500)
        for key in keys:
            tid = r.hget(key, "discord_thread_id")
            if tid:
                thread_ids.append(tid)
        if cursor == 0:
            break

    for tid in thread_ids:
        discord.delete_thread(tid)

    logger.info("Discord cleanup: deleted %d thread(s) for %s.", len(thread_ids), yesterday)

    # 2. Delete Redis keys
    patterns = [
        f"post:{yesterday}:*",
        f"known:{yesterday}",
        f"published:{yesterday}",
    ]

    deleted = 0
    for pattern in patterns:
        if "*" in pattern:
            cursor = 0
            while True:
                cursor, keys = r.scan(cursor, match=pattern, count=500)
                if keys:
                    r.delete(*keys)
                    deleted += len(keys)
                if cursor == 0:
                    break
        else:
            if r.delete(pattern):
                deleted += 1

    logger.info("Redis cleanup: deleted %d key(s) for %s.", deleted, yesterday)

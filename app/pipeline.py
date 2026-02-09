import json
import logging

import httpx

from app import discord, store
from app.config import settings
from app.fetcher import fetch_recent_posts
from app.scorer import score_posts

logger = logging.getLogger(__name__)


def run_pipeline() -> None:
    """Fetch -> filter -> score -> store -> publish cycle."""

    # 1. Fetch
    try:
        raw_posts = fetch_recent_posts()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            logger.warning("X API rate limited. Will retry next cycle.")
            return
        logger.error("X API error: %s", e)
        return
    except Exception:
        logger.error("Fetch failed.", exc_info=True)
        return

    if not raw_posts:
        logger.info("No posts fetched, skipping cycle.")
        return

    # 2. Filter out posts already seen in previous cycles
    new_posts = [p for p in raw_posts if not store.is_known(p["id"])]
    store.mark_known([p["id"] for p in new_posts])

    if not new_posts:
        logger.info("All %d fetched posts already known. Skipping.", len(raw_posts))
        return

    logger.info("Fetched %d posts, %d are new.", len(raw_posts), len(new_posts))

    # 3. Drop low-engagement posts before calling Gemini
    def _engagement(p: dict) -> int:
        m = p.get("public_metrics", {})
        return m.get("like_count", 0) + m.get("retweet_count", 0) + m.get("quote_count", 0)

    engaged = [p for p in new_posts if _engagement(p) >= settings.min_engagement]
    if not engaged:
        logger.info("All %d new posts below engagement threshold (%d). Skipping.",
                     len(new_posts), settings.min_engagement)
        return

    logger.info("Engagement filter: %d -> %d posts (min %d).",
                len(new_posts), len(engaged), settings.min_engagement)

    # 4. Score against ALIGNMENTS via Gemini
    try:
        scored = score_posts(engaged)
    except json.JSONDecodeError:
        logger.error("Gemini returned invalid JSON. Skipping cycle.")
        return
    except Exception:
        logger.error("Scoring failed.", exc_info=True)
        return

    if not scored:
        logger.info("No posts passed the relevance filter.")
        return

    # 5. Select top N
    top = scored[: settings.top_n]
    logger.info(
        "Top %d posts: %s",
        len(top),
        [(p.get("short_title", "?"), p.get("priority", "?")) for p in top],
    )

    # 6. Store and publish
    published_count = 0
    for post in top:
        try:
            is_new = store.save_post(post)
            if is_new:
                thread_id = discord.post_news(post)
                if thread_id:
                    post["discord_thread_id"] = thread_id
                    store.save_thread_id(post["id"], thread_id)
                store.publish_to_stream(post)
                logger.info(
                    "PUBLISHED [%s] %s\n  Link: %s\n  Text: %s\n  TLDR: %s",
                    post["id"],
                    post.get("short_title", ""),
                    f"https://x.com/i/status/{post['id']}",
                    post.get("text", "")[:280],
                    post.get("tldr", ""),
                )
                published_count += 1
            else:
                logger.info("Skipped (already published): [%s]", post["id"])
        except Exception:
            logger.error("Failed to store/publish post %s.", post["id"], exc_info=True)

    logger.info("Cycle complete. Published %d new post(s).", published_count)

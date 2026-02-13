import json
import logging

import httpx

from app import discord, store
from app.config import settings
from app.github_fetcher import fetch_all_github_items
from app.github_scorer import score_github_items

logger = logging.getLogger(__name__)


def run_github_pipeline() -> None:
    """Fetch -> dedup -> score -> store -> publish for GitHub."""

    # 1. Fetch
    try:
        raw_items = fetch_all_github_items()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            logger.warning(
                "GitHub API rate limited. Will retry next cycle.",
            )
            return
        logger.error("GitHub API error: %s", e)
        return
    except Exception:
        logger.error("GitHub fetch failed.", exc_info=True)
        return

    if not raw_items:
        logger.info("No GitHub items fetched, skipping cycle.")
        return

    # 2. Dedup
    new_items = [
        it for it in raw_items
        if not store.is_gh_known(it["id"])
    ]
    store.mark_gh_known([it["id"] for it in new_items])

    if not new_items:
        logger.info(
            "All %d GitHub items already known. Skipping.",
            len(raw_items),
        )
        return

    logger.info(
        "Fetched %d GitHub items, %d are new.",
        len(raw_items), len(new_items),
    )

    # 3. Score via Gemini (no engagement gate)
    try:
        scored = score_github_items(new_items)
    except json.JSONDecodeError:
        logger.error(
            "Gemini returned invalid JSON. Skipping cycle.",
        )
        return
    except Exception:
        logger.error("GitHub scoring failed.", exc_info=True)
        return

    if not scored:
        logger.info("No GitHub items passed the filter.")
        return

    # 4. Select top N
    top = scored[: settings.github_top_n]
    logger.info(
        "Top %d GitHub items: %s",
        len(top),
        [
            (p.get("short_title", "?"), p.get("priority", "?"))
            for p in top
        ],
    )

    # 5. Store and publish
    published_count = 0
    for post in top:
        try:
            is_new = store.save_gh_post(post)
            if is_new:
                thread_id = discord.post_github_news(post)
                if thread_id:
                    post["discord_thread_id"] = thread_id
                    store.save_gh_thread_id(
                        post["id"], thread_id,
                    )
                store.publish_gh_to_stream(post)
                logger.info(
                    "PUBLISHED GH [%s] %s\n  URL: %s\n"
                    "  TLDR: %s",
                    post["id"],
                    post.get("short_title", ""),
                    post.get("url", ""),
                    post.get("tldr", ""),
                )
                published_count += 1
            else:
                logger.info(
                    "Skipped (already published): [%s]",
                    post["id"],
                )
        except Exception:
            logger.error(
                "Failed to store/publish GH item %s.",
                post["id"],
                exc_info=True,
            )

    logger.info(
        "GitHub cycle complete. Published %d new item(s).",
        published_count,
    )

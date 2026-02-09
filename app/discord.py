import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

DISCORD_API = "https://discord.com/api/v10"


def _headers() -> dict:
    return {
        "Authorization": f"Bot {settings.discord_bot_token}",
        "Content-Type": "application/json",
    }


def _tweet_link(tweet_id: str) -> str:
    return f"https://x.com/i/status/{tweet_id}"


def post_news(post: dict) -> str | None:
    """Create a forum thread for the news item. Returns the thread ID or None."""
    if not settings.discord_bot_token or not settings.discord_channel_id:
        return None

    title = post.get("short_title", "News")[:100]
    link = _tweet_link(post["id"])
    tldr = post.get("tldr", "")
    priority = post.get("priority", "medium")
    tags = ", ".join(post.get("tags", []))
    reason = post.get("reason", "")

    lines = [f"**{title}**", ""]
    if tldr:
        lines.append(tldr)
        lines.append("")
    if reason:
        lines.append(f"> {reason}")
        lines.append("")
    if tags:
        lines.append(f"Tags: `{tags}`")
    lines.append(f"Priority: **{priority}**")
    lines.append("")
    lines.append(link)

    content = "\n".join(lines)

    # Create forum thread in the news channel
    try:
        resp = httpx.post(
            f"{DISCORD_API}/channels/{settings.discord_channel_id}/threads",
            headers=_headers(),
            json={"name": title, "message": {"content": content}},
            timeout=15,
        )
        resp.raise_for_status()
        thread_id = resp.json()["id"]
        logger.info("Created Discord thread %s: %s", thread_id, title)
        return thread_id
    except Exception:
        logger.error("Failed to create Discord thread.", exc_info=True)
        return None


def delete_thread(thread_id: str) -> None:
    """Delete a Discord thread/channel by ID."""
    if not settings.discord_bot_token or not thread_id:
        return
    try:
        resp = httpx.delete(
            f"{DISCORD_API}/channels/{thread_id}",
            headers=_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        logger.info("Deleted Discord thread: %s", thread_id)
    except Exception:
        logger.error("Failed to delete Discord thread %s.", thread_id, exc_info=True)

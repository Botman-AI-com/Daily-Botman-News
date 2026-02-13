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
    """Create a forum thread for a news item."""
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


TAG_COLORS = {
    "Release": "\U0001f534",
    "ClaudeCode": "\U0001f535",
    "Codex": "\U0001f7e2",
    "Changelog": "\U0001f7e1",
    "Feature": "\U0001f7e3",
    "BugFix": "\U0001f7e0",
    "Breaking": "\U0001f534",
    "MCP": "\U0001f535",
    "Performance": "\u26aa",
    "Security": "\U0001f534",
    "CLI": "\U0001f7e2",
    "Agent": "\U0001f7e3",
    "Model": "\U0001f7e1",
}

TYPE_EMOJI = {
    "release": "\U0001f680",
    "pr": "\U0001f500",
    "issue": "\U0001f41b",
}

PRIORITY_BADGE = {
    "high": "\U0001f525 High",
    "medium": "\u26a1 Medium",
}


def _format_tags(tags: list[str]) -> str:
    parts = []
    for tag in tags:
        dot = TAG_COLORS.get(tag, "\u26aa")
        parts.append(f"{dot} `{tag}`")
    return "  ".join(parts)


def post_github_news(post: dict) -> str | None:
    """Create a rich forum thread for a GitHub update."""
    if not settings.discord_bot_token or not settings.discord_channel_id:
        return None

    item_type = post.get("type", "issue")
    emoji = TYPE_EMOJI.get(item_type, "\U0001f4e6")
    repo = post.get("repo", "")
    raw_title = post.get("short_title", "News")
    priority = post.get("priority", "medium")
    tldr = post.get("tldr", "")
    reason = post.get("reason", "")
    tags = post.get("tags", [])
    tips = post.get("tips", "")
    url = post.get("url", "")
    badge = PRIORITY_BADGE.get(priority, priority)

    thread_name = (
        f"{emoji} {raw_title}"[:100]
    )

    lines = [
        f"{emoji}  **{raw_title}**",
        f"\U0001f4e6 `{repo}` \u2022 "
        f"`{item_type.upper()}` \u2022 {badge}",
        "\u2500" * 30,
    ]

    if tldr:
        lines.append("")
        lines.append("\U0001f4cb  **What Changed**")
        lines.append(tldr)

    if tips:
        lines.append("")
        lines.append("\U0001f4a1  **Tips & How to Use**")
        for tip in tips.split("|"):
            tip = tip.strip()
            if tip:
                lines.append(f"\u2022 {tip}")

    if reason:
        lines.append("")
        lines.append(f"> \U0001f4ac {reason}")

    if tags:
        lines.append("")
        lines.append(_format_tags(tags))

    if url:
        lines.append("")
        lines.append(f"\U0001f517 {url}")

    content = "\n".join(lines)

    try:
        resp = httpx.post(
            (
                f"{DISCORD_API}/channels"
                f"/{settings.discord_channel_id}/threads"
            ),
            headers=_headers(),
            json={
                "name": thread_name,
                "message": {"content": content},
            },
            timeout=15,
        )
        resp.raise_for_status()
        thread_id = resp.json()["id"]
        logger.info(
            "Created GH Discord thread %s: %s",
            thread_id, thread_name,
        )
        return thread_id
    except Exception:
        logger.error(
            "Failed to create GH Discord thread.",
            exc_info=True,
        )
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
        logger.error(
            "Failed to delete Discord thread %s.",
            thread_id, exc_info=True,
        )

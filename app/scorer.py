import json
import logging

from google import genai

from app.config import settings

logger = logging.getLogger(__name__)

client = genai.Client(api_key=settings.gemini_api_key)


def score_posts(posts: list[dict]) -> list[dict]:
    """Filter and score posts against ALIGNMENTS using Gemini. Returns relevant posts sorted by priority."""
    if not posts:
        return []

    tweet_list = "\n".join(
        f"[{i}] (id:{p['id']}) {p['text']}" for i, p in enumerate(posts)
    )

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=tweet_list,
        config={
            "system_instruction": settings.alignments,
            "response_mime_type": "application/json",
        },
    )

    scored_list = json.loads(response.text)

    post_map = {i: p for i, p in enumerate(posts)}
    priority_order = {"high": 0, "medium": 1}

    result = []
    for item in scored_list:
        idx = item["index"]
        if idx in post_map:
            enriched = post_map[idx].copy()
            enriched["priority"] = item["priority"]
            enriched["tags"] = item.get("tags", [])
            enriched["short_title"] = item.get("title", "")
            enriched["reason"] = item.get("reason", "")
            enriched["tldr"] = item.get("tldr", "")
            result.append(enriched)

    result.sort(key=lambda x: priority_order.get(x["priority"], 99))

    logger.info(
        "Scored %d posts, %d passed filter. Priorities: %s",
        len(posts),
        len(result),
        [f"{p['priority']}" for p in result],
    )
    return result

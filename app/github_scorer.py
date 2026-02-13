import json
import logging

from google import genai

from app.config import settings

logger = logging.getLogger(__name__)

client = genai.Client(api_key=settings.gemini_api_key)

GITHUB_FILTER_PROMPT = """\
You are a GitHub activity filter for a team of AI engineers \
building products with LLMs. Evaluate each GitHub item and \
return a JSON verdict.

## RULES
- Releases ALWAYS pass with priority "high".
- New features, breaking changes, new CLI commands, \
MCP integrations → high.
- Major bug fixes, community-supported feature requests → medium.
- FILTER OUT: dependabot PRs, typo fixes, doc-only changes, \
stale issues, CI-only changes.

## TAGS
Assign one or more tags from this list (use exactly these names):
Release, ClaudeCode, Codex, Changelog, Feature, BugFix, \
Breaking, MCP, Performance, Security, CLI, Agent, Model

## OUTPUT FORMAT
Return ONLY a valid JSON array of items that pass. \
If none pass, return [].
Each element:
{
  "index": <number>,
  "pass": true,
  "priority": "high" | "medium",
  "tags": ["Release", "ClaudeCode", ...],
  "title": "Short headline, max 100 chars",
  "reason": "One sentence why this matters.",
  "tldr": "2-3 sentence summary of what changed.",
  "tips": "1-2 practical tips on how the team could use this. \
Write as bullet points separated by | (pipe). \
Example: Update with claude update|Try the new /team command"
}

Be aggressive filtering. Ask: "Would this change how we \
build or use our tools tomorrow?" If no, filter it out.
"""


def score_github_items(items: list[dict]) -> list[dict]:
    """Filter and rank GitHub items via Gemini."""
    if not items:
        return []

    numbered = "\n".join(
        f"[{i}] (id:{it['id']}) [{it['type']}] "
        f"{it['title']}\n{it['body'][:500]}"
        for i, it in enumerate(items)
    )

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=numbered,
        config={
            "system_instruction": GITHUB_FILTER_PROMPT,
            "response_mime_type": "application/json",
        },
    )

    scored_list = json.loads(response.text)

    item_map = {i: it for i, it in enumerate(items)}
    priority_order = {"high": 0, "medium": 1}

    result = []
    for entry in scored_list:
        idx = entry["index"]
        if idx in item_map:
            enriched = item_map[idx].copy()
            enriched["priority"] = entry["priority"]
            enriched["tags"] = entry.get("tags", [])
            enriched["short_title"] = entry.get("title", "")
            enriched["reason"] = entry.get("reason", "")
            enriched["tldr"] = entry.get("tldr", "")
            enriched["tips"] = entry.get("tips", "")
            result.append(enriched)

    result.sort(
        key=lambda x: priority_order.get(x["priority"], 99),
    )

    logger.info(
        "Scored %d GH items, %d passed. Priorities: %s",
        len(items),
        len(result),
        [p["priority"] for p in result],
    )
    return result

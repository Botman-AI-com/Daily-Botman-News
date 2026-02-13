import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

GH_API = "https://api.github.com"


def _headers() -> dict:
    h = {"Accept": "application/vnd.github+json"}
    if settings.github_token:
        h["Authorization"] = f"Bearer {settings.github_token}"
    return h


def _parse_repos() -> list[str]:
    return [
        repo.strip()
        for repo in settings.github_repos.split(",")
        if repo.strip()
    ]


def _normalize(
    repo: str,
    item_type: str,
    number: int,
    raw: dict,
) -> dict:
    body = raw.get("body") or ""
    return {
        "id": f"gh:{repo}:{item_type}:{raw['id']}",
        "repo": repo,
        "type": item_type,
        "number": number,
        "title": raw.get("title") or raw.get("name", ""),
        "body": body[:2000],
        "url": raw.get("html_url", ""),
        "author": (raw.get("author") or raw.get("user") or {})
        .get("login", ""),
        "created_at": raw.get("created_at", ""),
        "labels": [
            lb["name"]
            for lb in raw.get("labels", [])
            if isinstance(lb, dict)
        ],
        "reactions_count": raw.get("reactions", {})
        .get("total_count", 0),
        "comments_count": raw.get("comments", 0),
    }


def fetch_releases(
    repo: str, since: datetime,
) -> list[dict]:
    url = f"{GH_API}/repos/{repo}/releases"
    resp = httpx.get(
        url,
        params={"per_page": 10},
        headers=_headers(),
        timeout=30,
    )
    resp.raise_for_status()

    items = []
    for release in resp.json():
        pub = release.get("published_at")
        if not pub:
            continue
        pub_dt = datetime.fromisoformat(
            pub.replace("Z", "+00:00")
        )
        if pub_dt > since:
            items.append(_normalize(repo, "release", 0, release))
    return items


def fetch_merged_prs(
    repo: str, since: datetime,
) -> list[dict]:
    url = f"{GH_API}/repos/{repo}/pulls"
    resp = httpx.get(
        url,
        params={
            "state": "closed",
            "sort": "updated",
            "direction": "desc",
            "per_page": 30,
        },
        headers=_headers(),
        timeout=30,
    )
    resp.raise_for_status()

    items = []
    for pr in resp.json():
        merged = pr.get("merged_at")
        if not merged:
            continue
        merged_dt = datetime.fromisoformat(
            merged.replace("Z", "+00:00")
        )
        if merged_dt > since:
            items.append(
                _normalize(repo, "pr", pr.get("number", 0), pr)
            )
    return items


def fetch_notable_issues(
    repo: str, since: datetime,
) -> list[dict]:
    url = f"{GH_API}/repos/{repo}/issues"
    resp = httpx.get(
        url,
        params={
            "sort": "updated",
            "direction": "desc",
            "since": since.isoformat(),
            "per_page": 30,
        },
        headers=_headers(),
        timeout=30,
    )
    resp.raise_for_status()

    items = []
    for issue in resp.json():
        if "pull_request" in issue:
            continue
        items.append(
            _normalize(
                repo, "issue", issue.get("number", 0), issue,
            )
        )
    return items


def fetch_all_github_items() -> list[dict]:
    """Fetch releases, merged PRs, and issues from all repos."""
    since = datetime.now(timezone.utc) - timedelta(
        minutes=settings.github_check_interval_minutes + 5,
    )
    repos = _parse_repos()
    all_items: list[dict] = []

    for repo in repos:
        fetchers = [
            ("releases", fetch_releases),
            ("merged PRs", fetch_merged_prs),
            ("issues", fetch_notable_issues),
        ]
        for label, fn in fetchers:
            try:
                items = fn(repo, since)
                all_items.extend(items)
                logger.info(
                    "Fetched %d %s from %s.",
                    len(items), label, repo,
                )
            except httpx.HTTPStatusError as e:
                code = e.response.status_code
                if code in (403, 429):
                    logger.warning(
                        "GitHub rate limited (%d) for %s %s.",
                        code, repo, label,
                    )
                else:
                    logger.error(
                        "GitHub API error %d for %s %s.",
                        code, repo, label,
                        exc_info=True,
                    )
            except Exception:
                logger.error(
                    "Failed fetching %s from %s.",
                    label, repo,
                    exc_info=True,
                )

    logger.info(
        "Total GitHub items fetched: %d.", len(all_items),
    )
    return all_items

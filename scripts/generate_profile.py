#!/usr/bin/env python3
"""Generate the dynamic terminal-profile SVG used by the profile README."""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


OWNER = os.environ.get("GITHUB_REPOSITORY_OWNER", "braucci")
ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "assets" / "terminal-profile-card.png"
OUTPUT = ROOT / "assets" / "terminal-profile.svg"
TOKEN = os.environ.get("GITHUB_TOKEN", "")


def get_json(url: str) -> object:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "braucci-profile-generator",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=30) as response:  # nosec B310 -- GitHub API URL is fixed
        return json.load(response)


def public_repositories() -> list[dict]:
    repositories: list[dict] = []
    page = 1
    while True:
        query = urlencode({"type": "owner", "per_page": 100, "page": page})
        data = get_json(f"https://api.github.com/users/{OWNER}/repos?{query}")
        if not data:
            return repositories
        repositories.extend(data)
        page += 1


def contributions_this_year() -> str:
    """Return public yearly contributions, falling back gracefully if unavailable."""
    if not TOKEN:
        return "—"

    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar { totalContributions }
        }
      }
    }
    """
    payload = json.dumps({"query": query, "variables": {"login": OWNER}}).encode()
    request = Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "braucci-profile-generator",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:  # nosec B310 -- fixed GitHub endpoint
            data = json.load(response)
        return f"{data['data']['user']['contributionsCollection']['contributionCalendar']['totalContributions']:,}"
    except Exception:
        return "—"


def metric(x: int, width: int, label: str, value: str) -> str:
    """Draw one live metric, hiding the fixed value in the background image."""
    center = x + width // 2
    return (
        f'<rect x="{x}" y="900" width="{width}" height="105" fill="#05090d"/>'
        f'<text x="{center}" y="938" text-anchor="middle" '
        'font-family="JetBrains Mono, Menlo, Consolas, monospace" font-size="20" '
        'fill="#c9c9c9">'
        f"{label}</text>"
        f'<text x="{center}" y="980" text-anchor="middle" '
        'font-family="JetBrains Mono, Menlo, Consolas, monospace" font-size="25" '
        'fill="#74d633">'
        f"{value}</text>"
    )


def main() -> None:
    if not CARD.exists():
        raise FileNotFoundError(f"Missing background card: {CARD}")

    repositories = public_repositories()
    repo_count = str(len(repositories))
    stars = f"{sum(repository['stargazers_count'] for repository in repositories):,}"
    contributions = contributions_this_year()
    updated = datetime.now(ZoneInfo("Europe/Rome")).strftime("%-d %b %Y")
    background = base64.b64encode(CARD.read_bytes()).decode("ascii")

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1536" height="1024" viewBox="0 0 1536 1024">
  <image width="1536" height="1024" href="data:image/png;base64,{background}"/>
  {metric(660, 180, 'Repos', repo_count)}
  {metric(845, 185, 'Stars', stars)}
  {metric(1035, 230, 'Contributions', contributions)}
  {metric(1270, 250, 'Last update', updated)}
</svg>
'''
    OUTPUT.write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    main()

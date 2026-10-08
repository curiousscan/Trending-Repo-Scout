#!/usr/bin/env python3
"""
CuriousScan Trending-Repo Scout
================================
Tracks the fastest-rising AI repositories on GitHub and spits out a daily
digest. No API key needed (uses the public GitHub Search API).

Usage:
    python scout.py                          # AI repos from the last 7 days
    python scout.py --days 3 --min-stars 100
    python scout.py --out digest.md          # write a markdown digest file
    python scout.py --json                   # machine-readable output

Stdlib only — no dependencies.
"""

import argparse
import json
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone

VERSION = "0.1.0"
API = "https://api.github.com/search/repositories"

AI_KEYWORDS = [
    "ai", "llm", "gpt", "agent", "agents", "diffusion", "transformer",
    "rag", "vector", "embedding", "chatbot", "inference", "fine-tune",
    "finetune", "lora", "stable-diffusion", "whisper", "tts",
    "text-to-image", "multimodal", "copilot",
]


def is_ai_repo(repo):
    """Heuristic: AI-related if keywords hit name/description/topics."""
    text = " ".join(
        [
            repo.get("full_name", ""),
            repo.get("description") or "",
            " ".join(repo.get("topics", [])),
            repo.get("language") or "",
        ]
    ).lower()
    return any(k in text for k in AI_KEYWORDS)


def search(days, min_stars, per_page=50):
    """Repos created in the last N days, sorted by stars (proxy for trending)."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    q = f"created:>{since} stars:>={min_stars}"
    params = urllib.parse.urlencode(
        {"q": q, "sort": "stars", "order": "desc", "per_page": per_page}
    )
    req = urllib.request.Request(
        f"{API}?{params}",
        headers={
            "User-Agent": f"curiousscan-repo-scout/{VERSION}",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    items = data.get("items", [])
    remaining = resp.headers.get("X-RateLimit-Remaining")
    return items, remaining


def to_digest(repos):
    out = []
    for r in repos:
        out.append(
            {
                "name": r["full_name"],
                "url": r["html_url"],
                "stars": r["stargazers_count"],
                "language": r.get("language"),
                "description": (r.get("description") or "").strip(),
            }
        )
    return out


def to_markdown(digest, days):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        f"# Trending AI Repos — {today} (last {days}d)",
        "",
        f"_Curated by CuriousScan Repo Scout · {len(digest)} repos_",
        "",
    ]
    for d in digest:
        lang = f" · {d['language']}" if d["language"] else ""
        lines.append(f"## [{d['name']}]({d['url']}) — ⭐ {d['stars']:,}{lang}")
        if d["description"]:
            lines.append(f"{d['description']}")
        lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(
        description="Daily digest of trending AI repos on GitHub."
    )
    ap.add_argument("--days", type=int, default=7, help="Lookback window (default 7).")
    ap.add_argument("--min-stars", type=int, default=20,
                    help="Minimum stars to include (default 20).")
    ap.add_argument("--no-filter", action="store_true",
                    help="Skip the AI keyword filter; show all trending repos.")
    ap.add_argument("--out", default=None, help="Write markdown digest to file.")
    ap.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = ap.parse_args()

    try:
        items, remaining = search(args.days, args.min_stars)
    except Exception as exc:
        print(f"[!] GitHub API error: {exc}", file=sys.stderr)
        sys.exit(1)

    repos = [r for r in items if args.no_filter or is_ai_repo(r)]
    digest = to_digest(repos)

    if args.json:
        print(json.dumps(digest, indent=2))
    elif args.out:
        with open(args.out, "w") as f:
            f.write(to_markdown(digest, args.days))
        print(f"Wrote {len(digest)} repos to {args.out}")
    else:
        print(to_markdown(digest, args.days))

    if remaining is not None:
        print(f"\n(API calls remaining this hour: {remaining})", file=sys.stderr)


if __name__ == "__main__":
    main()

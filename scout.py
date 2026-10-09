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
    python scout.py --claude-filter          # Claude rates signal-vs-hype (needs ANTHROPIC_API_KEY)

Stdlib only — no dependencies.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone

VERSION = "0.2.0"
API = "https://api.github.com/search/repositories"

# Claude hype-filter (optional): Haiku judges signal-vs-hype per repo — cheap
# classification work on the cheap model, exactly the Haiku-vs-Sonnet cost
# routing we recommend. Stdlib only, no SDK. Verify current model IDs at
# https://docs.anthropic.com/en/docs/about-claude/models/overview
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_CLAUDE_MODEL = "claude-haiku-4-5"
CLAUDE_FILTER_CAP = 25  # bound API cost: rate at most this many repos per run


def get_anthropic_key():
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        print(
            "ERROR: --claude-filter needs ANTHROPIC_API_KEY.\n"
            "Get one at https://console.anthropic.com/ then run:\n"
            '  export ANTHROPIC_API_KEY="sk-ant-..."',
            file=sys.stderr,
        )
        sys.exit(2)
    return key


def claude_rate_repos(api_key, model, digest):
    """Ask Claude to rate each repo REAL (signal) or HYPE. Returns verdict dicts."""
    batch = digest[:CLAUDE_FILTER_CAP]
    listing = "\n".join(
        f"{i+1}. {d['name']} ({d['language'] or 'n/a'}, {d['stars']} stars): "
        f"{d['description'] or 'no description'}"
        for i, d in enumerate(batch)
    )
    payload = json.dumps(
        {
            "model": model,
            "max_tokens": 2000,
            "system": (
                "You are a cynical open-source analyst. For each repo, judge "
                "whether it is real AI signal (working code, real utility) or "
                "hype (marketing fluff, vaporware, star-bait README). Reply with "
                "ONLY a JSON array: "
                '[{"name": "<full repo name>", "verdict": "REAL" or "HYPE", '
                '"reason": "<=12 words>"}]. No other text.'
            ),
            "messages": [
                {"role": "user", "content": f"Rate these repos:\n\n{listing}"}
            ],
        }
    ).encode()
    req = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.load(resp)
        text = "".join(
            b.get("text", "")
            for b in data.get("content", [])
            if b.get("type") == "text"
        ).strip()
        verdicts = json.loads(text[text.index("["):text.rindex("]") + 1])
        return {v["name"]: v for v in verdicts if "name" in v}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")[:300]
        raise RuntimeError(f"Claude API -> HTTP {exc.code}: {body}")
    except (ValueError, KeyError) as exc:
        raise RuntimeError(f"Claude returned an unparseable verdict: {exc}")

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


def to_markdown(digest, days, verdicts=None):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        f"# Trending AI Repos — {today} (last {days}d)",
        "",
        f"_Curated by CuriousScan Repo Scout · {len(digest)} repos_",
        "",
    ]
    for d in digest:
        lang = f" · {d['language']}" if d["language"] else ""
        tag = ""
        if verdicts and d["name"] in verdicts:
            v = verdicts[d["name"]]
            icon = "✅" if v.get("verdict") == "REAL" else "⚠️"
            tag = f" {icon} {v.get('verdict')}: {v.get('reason', '')}"
        lines.append(f"## [{d['name']}]({d['url']}) — ⭐ {d['stars']:,}{lang}{tag}")
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
    ap.add_argument("--claude-filter", action="store_true",
                    help="Claude (Haiku) rates each repo REAL/HYPE for signal-vs-hype "
                         "(needs ANTHROPIC_API_KEY).")
    ap.add_argument("--claude-model", default=DEFAULT_CLAUDE_MODEL,
                    help=f"Claude model for --claude-filter (default {DEFAULT_CLAUDE_MODEL}).")
    args = ap.parse_args()

    try:
        items, remaining = search(args.days, args.min_stars)
    except Exception as exc:
        print(f"[!] GitHub API error: {exc}", file=sys.stderr)
        sys.exit(1)

    repos = [r for r in items if args.no_filter or is_ai_repo(r)]
    digest = to_digest(repos)

    verdicts = None
    if args.claude_filter and digest:
        try:
            verdicts = claude_rate_repos(get_anthropic_key(), args.claude_model, digest)
            for d in digest:
                if d["name"] in verdicts:
                    d["signal"] = verdicts[d["name"]].get("verdict")
        except RuntimeError as exc:
            print(f"[!] Claude filter failed: {exc}", file=sys.stderr)
            print("[!] Continuing without signal ratings.", file=sys.stderr)

    if args.json:
        print(json.dumps(digest, indent=2))
    elif args.out:
        with open(args.out, "w") as f:
            f.write(to_markdown(digest, args.days, verdicts))
        print(f"Wrote {len(digest)} repos to {args.out}")
    else:
        print(to_markdown(digest, args.days, verdicts))

    if remaining is not None:
        print(f"\n(API calls remaining this hour: {remaining})", file=sys.stderr)


if __name__ == "__main__":
    main()

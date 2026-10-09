# CuriousScan Trending-Repo Scout

Tracks the fastest-rising AI repositories on GitHub and spits out a daily
digest. No API key needed.

```bash
# AI repos trending over the last 7 days
python scout.py

# tighter window, higher bar
python scout.py --days 3 --min-stars 100

# save a markdown digest (great for a cron job)
python scout.py --out digest.md

# machine-readable
python scout.py --json > repos.json

# let Claude (Haiku) rate every repo REAL vs HYPE for signal-vs-hype
export ANTHROPIC_API_KEY="sk-ant-..."
python scout.py --claude-filter
```

## Claude hype-filter (optional)

Star counts can be gamed and READMEs can lie. With an Anthropic API key,
`--claude-filter` sends the digest to Claude Haiku — cheap classification
work on the cheap model — which rates each repo `REAL` (working code, real
utility) or `HYPE` (marketing fluff, star-bait). Verdicts are labeled in the
digest, never silently dropped. Rates at most 25 repos per run to bound API
cost; `--claude-model` overrides the default (`claude-haiku-4-5`). Still
stdlib only — direct Messages API calls, no SDK.

## How it works

- Queries GitHub's public Search API for repos created in the last N days,
  sorted by stars (a solid proxy for "trending")
- Filters to AI-related repos via keyword matching on name, description,
  and topics (`--no-filter` disables this)
- Renders a markdown digest with stars, language, and descriptions

## Notes

- Unauthenticated GitHub API: 60 requests/hour — plenty for a daily digest.
  If you ever need more, add a personal access token as an
  `Authorization: Bearer <token>` header in `search()`.

## Requirements

Python 3.8+. Stdlib only — zero dependencies.

## License

MIT — see `LICENSE`.

---
Built by [CuriousScan](https://curiousscan.in) — *Less noise. More signal.*

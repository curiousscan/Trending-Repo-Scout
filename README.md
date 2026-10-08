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
```

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

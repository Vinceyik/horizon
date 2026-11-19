# Horizon — personal daily briefing

A fork of [Thysrael/Horizon](https://github.com/Thysrael/Horizon) (MIT) configured as a personal daily briefing, published to GitHub Pages.

**Live:** https://vinceyik.github.io/horizon/

Three tabs, Traditional Chinese, one run per day at ~08:00 Hong Kong time:

| Tab | Covers | Sources |
|---|---|---|
| 時尚與精品 | Watches, apparel, jewellery, auctions, collaborations | Hodinkee, Hypebeast, Vogue |
| AI 前沿 | Model releases, APIs, open-source tooling, benchmarks | OpenAI Blog, Hugging Face, Anthropic (via Google News), GitHub Trending, Hacker News |
| 天然氣數據 | US storage, Henry Hub prices, LNG flows, degree days | NGI, OilPrice, EIA Today in Energy, Google News |

Each tab gets a 2–3 sentence executive summary and a ranked item list with the original title, a 30-character Chinese blurb, and the source link. The natural-gas tab adds a numeric data block when the source contains figures.

## What this fork changes

- Three profiles: `fashion`, `ai-news`, `energy-data` (`profiles/`)
- A personal config (`data/config.personal.json`)
- A `zh-Hant` output language, including a Simplified-to-Traditional guard
- `src/site/` — builds `web/data.json` and a daily archive at the end of each run
- `web/` — a hand-written static front-end (no CDN, no build step)
- `.github/workflows/daily_update.yml` — daily run and Pages deploy

Everything else is upstream Horizon, kept close enough to merge from `upstream/main`.

## Setup

See [docs/setup.md](docs/setup.md).

## Design and plan

- `docs/superpowers/specs/2026-11-19-daily-briefing-design.md`
- `docs/superpowers/plans/2026-11-19-daily-briefing.md`

## Local preview

```bash
cp web/data.sample.json web/data.json
cd web && python -m http.server 8099
```

Then open http://localhost:8099/.

## Upstream

```bash
git remote add upstream https://github.com/Thysrael/Horizon.git
git fetch upstream
```

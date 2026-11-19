# Setup

This fork turns [Horizon](https://github.com/Thysrael/Horizon) into a personal daily briefing covering **fashion & watches**, **AI**, and **natural gas data**, published to GitHub Pages at `https://vinceyik.github.io/horizon/`.

## 1. Repository

The repo is `Vinceyik/horizon`, branch `main`, with the work on `personal/briefing`.

Keep upstream reachable for future merges:

```bash
git remote add upstream https://github.com/Thysrael/Horizon.git
git fetch upstream
```

## 2. Secrets

Repository → Settings → Secrets and variables → Actions → New repository secret.

| Secret | Required | What it is |
|---|---|---|
| `OPENAI_API_KEY` | one of these | An OpenAI-compatible key. The default config points at OpenRouter (`https://openrouter.ai/api/v1`), so an [OpenRouter](https://openrouter.ai/keys) key is the intended value. |
| `GOOGLE_API_KEY` | one of these | A Gemini key. Only useful if Gemini accepts your region; Hong Kong is not on Google's supported-region list as of 2026-11. |
| `APIFY_TOKEN` | no | Only needed if you enable `sources.twitter` in `data/config.personal.json`. |

`GITHUB_TOKEN` is provided by Actions; do not add it.

## 3. GitHub Pages

Settings → Pages → **Build and deployment**:

- Source: **Deploy from a branch**
- Branch: **`gh-pages`**, folder **`/ (root)`**

Do not choose "GitHub Actions". The workflow publishes to the `gh-pages` branch itself.

The first deploy creates `gh-pages`; until then the Pages settings page may show nothing to select.

## 4. First run

Actions → **Daily Briefing** → Run workflow → leave `hours` at `26`.

It will:

1. copy `data/config.personal.json` over the gitignored `data/config.json`
2. run `uv run horizon --hours 26`
3. write `web/data.json` and `web/archive/<date>.json`
4. deploy `web/` to `gh-pages`

Afterwards, open `https://vinceyik.github.io/horizon/`.

## 5. Changing what you read

Everything editorial lives in `data/config.personal.json`. Edit that file, not `data/config.json` (it is generated and gitignored).

- **Add a feed** — append to `sources.rss` with `name`, `url`, `category`, `profile`.
- **Change the mix** — `digest.category_groups.<group>.limit` caps how many items each tab gets; `max_items` caps the day.
- **Tighten quality** — raise `processing.profile_settings.<profile>.threshold`.
- **Switch model or provider** — the `ai` block. For DeepSeek: `provider: "openai"`, `base_url: "https://api.deepseek.com"`, `model: "deepseek-v4-flash"`, `api_key_env: "DEEPSEEK_API_KEY"`.

Prompts live in `profiles/fashion`, `profiles/ai-news`, `profiles/energy-data`, each with `match.md`, `analysis.md`, `enrichment.md`.

## 6. Caveats

- **Scheduling is approximate.** The cron is `0 0 * * *` (08:00 HKT), but GitHub can start a scheduled job 5–30 minutes late. The 26-hour lookback absorbs the drift.
- **Free tier.** Actions minutes and Pages are free on a public repo. The LLM is not: the daily run makes roughly 20–40 scoring calls, up to 18 enrichment calls, and 3 summary calls. Keep `max_items` low if you use a metered key.
- **X / Twitter is off.** Nitter public instances return 410 and RSSHub's public Twitter route is unreliable, so the config uses Apify instead, disabled by default.
- **No backfill.** Each run writes one archive file for its own date. Re-running does not fill past days.
- **Traditional Chinese is enforced.** `src/ai/localization.py` converts any Simplified characters in `zh-Hant` output, so a model slip cannot reach the page.

## 7. Revoke the setup token

The personal access token used to create and push this repo is not stored in the project. Revoke it at Settings → Developer settings → Personal access tokens once you are done.

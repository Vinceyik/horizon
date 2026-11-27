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
| `OPENCODE_API_KEY` | yes, by default | An [OpenCode Go](https://opencode.ai/console) key. The default config calls `https://opencode.ai/inference/go/openai/v1` with `deepseek-v4.1-flash`. |
| `OPENAI_API_KEY` | alternative | Any OpenAI-compatible key, for example [OpenRouter](https://openrouter.ai/keys). Swap `base_url`, `model` and `api_key_env` in the config to use it. |
| `GOOGLE_API_KEY` | alternative | A Gemini key. Only useful if Gemini accepts your region; Hong Kong is not on Google's supported-region list as of 2026-11. |
| `APIFY_TOKEN` | no | Only needed if you enable `sources.twitter` in `data/config.personal.json`. |
| `DEEPSEEK_API_KEY` | no | Needed only if you point `ai` at DeepSeek directly instead of through OpenCode Go. |
| `ANTHROPIC_API_KEY` | no | Needed only if you switch the `ai` block to Anthropic. |

The workflow exports every name in this table, so switching provider is the three config fields below plus the matching secret.

**About reusing an OpenCode Go subscription:** it works, and it shares your monthly Go allowance with your coding. A daily briefing uses roughly 10–12 million tokens a month, which is a noticeable slice of a Go plan. Go is also positioned for coding agents and monitors traffic for abuse, so a news summariser is outside its intended use. If either matters, point `ai` at a separate DeepSeek or OpenRouter key instead — that is a three-field change.

`GITHUB_TOKEN` is provided by Actions; do not add it.

## 3. GitHub Pages

Settings → Pages → **Build and deployment**:

- Source: **Deploy from a branch**
- Branch: **`gh-pages`**, folder **`/ (root)`**

Do not choose "GitHub Actions". The workflow publishes to the `gh-pages` branch itself.

The first deploy creates `gh-pages`; until then the Pages settings page may show nothing to select.

## 4. First run

**The workflow must exist on the default branch.** GitHub only lists a `workflow_dispatch` workflow and only runs its schedule when the workflow file is on `main`. Merge `personal/briefing` into `main` first.

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
- **Switch model or provider** — the `ai` block. The default is OpenCode Go: `provider: "openai"`, `base_url: "https://opencode.ai/inference/go/openai/v1"`, `model: "deepseek-v4.1-flash"`, `api_key_env: "OPENCODE_API_KEY"`. Another Go model id (for example `glm-5.3-flash` or `kimi-k3`) is a one-word change. For DeepSeek direct: `base_url: "https://api.deepseek.com"`, `model: "deepseek-v4-flash"` (upstream's default), `api_key_env: "DEEPSEEK_API_KEY"`.

Prompts live in `profiles/fashion`, `profiles/ai-news`, `profiles/energy-data`, each with `match.md`, `analysis.md`, `enrichment.md`.

The published files land in `web/` by default. Set `HORIZON_SITE_DIR` to write them elsewhere; the workflow and the front-end both assume `web/`.

## 6. Caveats

- **Scheduling is approximate.** The cron is `0 22 * * *` (06:00 HKT). This repo's scheduled runs have started 5–8 hours late, so expect the briefing between 08:00 and 14:00 Hong Kong time. Use **Run workflow** when you want it now.
- **Free tier.** Actions minutes and Pages are free on a public repo. The LLM is not: the daily run makes roughly 20–40 scoring calls, up to 18 enrichment calls, and 3 summary calls. Keep `max_items` low if you use a metered key.
- **X / Twitter is off.** Nitter public instances return 410 and RSSHub's public Twitter route is unreliable, so the config uses Apify instead, disabled by default.
- **No backfill.** Each run writes one archive file for its own date. Re-running does not fill past days.
- **Traditional Chinese is enforced.** `src/ai/localization.py` converts any Simplified characters in `zh-Hant` output, so a model slip cannot reach the page.

## 7. Revoke the setup token

The personal access token used to create and push this repo is not stored in the project. Revoke it at Settings → Developer settings → Personal access tokens once you are done.

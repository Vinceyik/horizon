# Personal Daily Briefing — Design

Date: 2026-11-19
Status: builder-checked, awaiting approval
Base: `Thysrael/Horizon` @ `12d5fbde` (MIT), cloned to `C:\Users\pos\projects\horizon`
Target repo: `Vinceyik/horizon` → `https://vinceyik.github.io/horizon/`

## 1. Intent

A personal, daily-updated briefing site that runs for free on GitHub Actions and GitHub Pages, covering three interests: **fashion & watches**, **AI frontier**, and **natural gas market data**. Output is Traditional Chinese (Hong Kong), readable on phone and desktop.

The owner is not a maintainer of Horizon and does not want to fork-maintain a parallel pipeline. The value is the editorial layer (what gets in, how it is written, how it is read), not the plumbing.

## 2. Why not build from scratch

Horizon already implements collection (10 scrapers), AI scoring, profile routing, threshold filtering, topic dedup, enrichment, bilingual Markdown output, a GitHub Actions template, and GitHub Pages deployment. Rebuilding those would cost weeks and produce a worse system.

Therefore: **fork Horizon and extend it**. Every change keeps upstream files touched to a minimum and prefers new files over edits, so `git merge upstream/main` stays cheap.

## 3. Goals

- One scheduled run produces a briefing for the last ~26 hours.
- The public site shows three tabs: 時尚與精品, AI 前沿, 天然氣數據.
- Each tab has a 2–3 sentence executive summary plus a ranked item list: original title, 30-character Chinese blurb, source, link.
- Natural-gas tab includes a numeric bullet list (BCF storage change, % moves, Henry Hub price, weather-driven demand, LNG flows) when the source contains such figures.
- Runs daily at ~08:00 HKT, costs 0 within free tiers, and needs no server.
- Traditional Chinese, HK financial vocabulary, not Simplified.

## 4. Non-goals

- No email, webhook, WeChat, Telegram bot, or MCP delivery in v1 (upstream supports them; leave disabled).
- No Reddit, Telegram, OpenBB, GDELT, OSS Insight sources in v1.
- No user accounts, comments, or search.
- **No backfill.** The archive starts at the first run and grows one file per day. Re-running for a past date is out of scope.
- No mobile app, no PWA offline mode.
- No changes to Horizon's scoring rubric *concept*; only new profile rubrics.

## 5. Anti-goals

Failures even if the site technically renders:

- Any daily step that needs a human to fix a broken third-party instance.
- A briefing dominated by marketing copy, press releases, or celebrity gossip.
- Numbers quoted without a baseline or comparison.
- Simplified Chinese leaking into the page.
- A category silently disappearing from the page.

## 6. Constraints

- **Free tier only.** Public repo → GitHub Actions minutes and Pages are free. LLM API is the only real cost; must fit a free tier or near-zero spend.
- **Hong Kong is not in Gemini API's supported-region list** as of writing. The LLM must be swappable by config, and the documented default must be reachable from HK. Recommended: OpenRouter free models, DeepSeek, or Gemini if the key works.
- **GitHub cron is best-effort.** 08:00 HKT is a target, not a guarantee; expect 5–30 min drift.
- **Upstream is active** (pushed daily). Minimal diffs.
- Windows dev machine; CI is Ubuntu.

## 7. Decisions

| Decision | Value |
|---|---|
| Base repo | Fork of `Thysrael/Horizon`, branch `personal/briefing` |
| Config format | Horizon's `data/config.json` (JSON). No YAML loader. |
| Config in git | `data/config.personal.json` committed; workflow copies it to the gitignored `data/config.json` |
| Digest grouping | `digest.group_by: "category"`; group ids are `fashion` / `ai` / `natgas` |
| Category ↔ profile | Every source is pinned explicitly; profile ids equal category ids (`fashion`, `ai-news` → category `ai`, `energy-data` → category `natgas`) |
| Tab names | `digest.category_groups.<id>.name` holds the Chinese label (single string; the site is zh-Hant only, so no per-language map is needed) |
| Editorial units | Three new profiles: `fashion`, `ai-news`, `energy-data` |
| Output language | `zh-Hant` only (English off) |
| Publisher | In-process at the end of `HorizonOrchestrator.run()`. No second workflow step, no intermediate file. |
| Group overviews | Generated inside the run with `self.ai_client`; `DailySummarizer` stays client-free |
| Site output dir | `web/` (not `docs/`), deployed to `gh-pages` |
| Front-end | Hand-written HTML/CSS/JS, no CDN, no build step |
| X / Twitter | Apify only, disabled by default; no Nitter, no RSSHub |
| Upstream docs site | `.github/workflows/deploy-docs.yml` disabled; `gh-pages` is owned solely by the daily workflow |
| Item cap | `max_items: 18` |

## 8. Architecture

```
GitHub Actions (cron 0 0 * * *)
  └─ uv run horizon --hours 26
       ├─ scrapers/         (rss, hackernews, github)   ← existing
       ├─ ai/classifier     → profile per item           ← existing
       ├─ ai/analyzer       → 0–10 score                 ← existing
       ├─ filtering + topic dedup                        ← existing
       ├─ ai/enricher       → summary + blurb + data     ← profile prompts, existing
       ├─ orchestrator      → 3 × group overview (AI)    ← new call
       ├─ ai/summarizer     → Markdown (secondary)       ← extended labels only
       └─ horizon_site.publish → web/data.json + archive ← new, in-process
  └─ peaceiris/actions-gh-pages  publish_dir: ./web  keep_files: true
```

`web/index.html` fetches `data.json` at runtime; no server rendering. The Markdown summary is still produced because upstream does it and it costs nothing, but nothing reads it on the site.

## 9. Sources (v1, all verified reachable on 2026-11-19)

### fashion — category `fashion`, profile `fashion`

| Name | URL | Status |
|---|---|---|
| Hodinkee | `https://www.hodinkee.com/articles.rss` | 200 |
| Hypebeast | `https://hypebeast.com/feed` | 200 |
| Vogue | `https://www.vogue.com/feed/rss` | 200 |

### ai — category `ai`, profile `ai-news`

| Name | URL | Status |
|---|---|---|
| OpenAI Blog | `https://openai.com/blog/rss.xml` | 200 |
| Hugging Face Blog | `https://huggingface.co/blog/feed.xml` | 200 |
| Anthropic News (via Google News) | `https://news.google.com/rss/search?q=Anthropic+when:2d&hl=en-US&gl=US&ceid=US:en` | 200 |
| GitHub Trending | `https://mshibanami.github.io/GitHubTrendingRSS/daily/all.xml` | 200 |
| Hacker News | built-in, `min_score: 150` | — |

Rejected: `anthropic.com/news/rss.xml` (404), `techcrunch.com/.../feed/` (403).

### natgas — category `natgas`, profile `energy-data`

| Name | URL | Status |
|---|---|---|
| Natural Gas Intelligence | `https://www.naturalgasintel.com/feed/` | 200 |
| OilPrice.com | `https://oilprice.com/rss/main` | 200 |
| EIA Today in Energy | `https://www.eia.gov/rss/todayinenergy.xml` | 200 |
| Natural gas (via Google News) | `https://news.google.com/rss/search?q=%22natural+gas%22+Henry+Hub+when:2d&hl=en-US&gl=US&ceid=US:en` | 200 |
| X accounts (optional) | Apify `altimis/scweet`, env `APIFY_TOKEN` | needs paid/free Apify |

Rejected: EIA weekly storage report has no RSS (`eia.gov/rss/naturalgas.xml` → 404). v1 reads the weekly number from NGI/OilPrice/EIA Today coverage; an EIA API v2 source is a later option, not v1.

**Google News entries are plain `sources.rss` items**, not `sources.google_news` — the built-in scraper holds a single query, and we need two. Caveats accepted: the `when:2d` window is wider than the 26 h run (upstream `seen.json` dedups repeats by URL), and the item link is a `news.google.com` redirect that resolves to the publisher. If the redirect proves annoying in practice, swap to the publisher's own feed.

## 10. Profiles (new, Markdown prompts)

Each profile is a directory `profiles/<id>/` with `profile.json`, `match.md`, `analysis.md`, `enrichment.md`, mirroring upstream shape.

**`fashion`**
- match: watches, apparel, jewellery, auctions, collaborations, runway-to-retail product news.
- analysis: reject celebrity styling, listicles, affiliate round-ups, "best of" SEO pages, resale hype without data.
- enrichment: `summary` (primary) + `blurb` (≤30 Chinese characters) + optional `data_points` for auction prices and release dates.

**`ai-news`**
- match: model releases, API/SDK changes, open-source tooling, benchmarks, safety/regulation with concrete content.
- analysis: reject pure marketing, funding announcements with no product, "AI will change everything" opinion, webinar ads.
- enrichment: `summary` + `blurb` + optional `data_points` (benchmark deltas, pricing, context length).

**`energy-data`**
- match: US natural gas storage, Henry Hub/TTF/JKM prices, LNG export flows, heating/cooling degree days, pipeline and export-terminal capacity.
- analysis: score up items with a specific figure **and** a baseline (WoW/YoY/consensus); score down items with "surged"/"plunged" and no number.
- enrichment: `summary` + `blurb` + **optional** `data_points` list, prompt-instructed to include a bullet whenever a figure exists.

`data_points` is **optional, not required**. A required block the model cannot fill fails the item (upstream drops failed enrichments), which would delete numberless-but-useful natgas items and pressure the model to invent numbers — both anti-goals. The UI hides an empty list. Block shape: `id: data_points`, `type: section`, `optional: true`; the prompt asks for `- label: value (change)` lines, one per row, ≤40 characters each. A native list type is used only if the block schema already supports one.

## 11. Traditional Chinese (zh-Hant)

Horizon today forces `zh` output to Simplified (`src/ai/localization.py` uses OpenCC `t2s`; `src/ai/prompting/enrichment.py` names the language "Simplified Chinese").

Plan: introduce a distinct language tag `zh-Hant` rather than mutating `zh`.

Files to touch:
1. `data/config.personal.json` → `ai.languages: ["zh-Hant"]`.
2. `src/ai/prompting/enrichment.py` → language-name map gains `zh-Hant: "Traditional Chinese (Hong Kong)"`; instruction adds "Use Hong Kong financial terminology (期貨、庫存、出口、需求), no Simplified characters."
3. `src/ai/summarizer.py` → `LABELS` gains a `zh-Hant` entry; `if language == "zh"` branches become `language in {"zh", "zh-Hant"}`.
4. `src/ai/localization.py` → `normalize_language` converts only `zh`; add a `s2t` pass for `zh-Hant` so a model slip cannot leak Simplified into the page.
5. `profiles/*/profile.json` → `display_names` gains `zh-Hant`.
6. Any other module that switches on language (`grep 'language =='` and `'"zh"'` under `src/ai/`) — same treatment.

Acceptance: a run's `data.json` contains no Simplified-only characters. Spot-check set: 与/與, 为/為, 国/國, 电/電, 数/數, 发/發.

## 12. Per-category executive summary

`DailySummarizer.__init__` takes only `profile_names` and `profile_order` — it holds no AI client. The overviews therefore live in the orchestrator, which already owns `self.ai_client`.

New module `horizon_site/overview.py`:

```
async def generate_group_overviews(ai_client, groups, language) -> dict[str, str]
```

- Called in `HorizonOrchestrator.run()` after filtering, before summarisation, on the final selected items.
- 3 calls per run, one per configured group, executed sequentially with the existing throttle.
- Input: group name + the group's item titles and summaries (already enriched).
- Output: 2–3 sentences, ≤120 Chinese characters, no bullets, no headline restating.
- A failed call yields an empty string; the UI hides the block. The run does not fail.
- The same dict is handed to the summarizer (for Markdown) and to the publisher (for JSON).

## 13. Site data contract (`web/data.json`)

The publisher always emits all three configured groups, in `digest.category_groups` order, even when a group has no items — that is how a category stays visible instead of silently vanishing.

```jsonc
{
  "generatedAt": "2026-11-19T08:12:31+08:00",
  "date": "2026-11-19",
  "language": "zh-Hant",
  "totalFetched": 214,
  "selected": 17,
  "groups": [
    {
      "id": "fashion",
      "name": "時尚與精品",
      "overview": "…",
      "status": "ok",              // "ok" | "empty" | "failed"
      "note": null,                // 今日無新內容 / 來源暫時無法讀取
      "items": [
        {
          "title": "中文標題",
          "originalTitle": "Original English title",
          "url": "https://…",
          "source": "Hodinkee",
          "score": 8,
          "blurb": "30 字以內短評",
          "summary": "一段落摘要",
          "dataPoints": ["庫存 +52 BCF（vs 五年均值 +18）"],
          "publishedAt": "2026-11-18T22:10:00Z"
        }
      ]
    }
  ],
  "failures": [{ "source": "twitter", "reason": "APIFY_TOKEN missing" }]
}
```

- `status: "empty"` = fetched fine, nothing passed the threshold or dedup.
- `status: "failed"` = every source feeding that category errored; `note` says so.
- `failures` carries **fetch errors only**. Disabled sources are not failures and do not appear.
- `generatedAt` is HKT, derived from the run clock, not from the LLM.

Archive: each run also writes `web/archive/YYYY-MM-DD.json`, same shape, one file per run date. Nothing rewrites a past day.

## 14. Front-end

Files: `web/index.html`, `web/assets/app.js`, `web/assets/style.css`, `web/data.sample.json`.

- Mobile-first, single column ≥ 360 px, max width 720 px.
- Tabs across the three groups, `role="tablist"`, arrow-key navigation, deep-link via `#fashion`.
- Item card: Chinese title (link), original title in muted small text, source + score badge, blurb, expandable summary, `dataPoints` list.
- Dark mode: toggle + `prefers-color-scheme` default, persisted in `localStorage` under `briefing-theme`, driven by CSS custom properties on `:root[data-theme]`.
- "最後更新" in HKT from `generatedAt`, plus the item counts.
- Date selector for the last 14 archived days (`?date=YYYY-MM-DD`). Each entry is probed with a `HEAD`; missing days stay hidden. Hidden entirely when no archive exists.
- No CDN, no framework, no build step. Total JS < 15 KB.
- States: no data → message; fetch error → retry button; `status: "empty"` → "今日無新內容"; `status: "failed"` → muted warning; `failures` → one muted line at the foot.

## 15. Workflow (`.github/workflows/daily_update.yml`)

```yaml
on:
  schedule: [{ cron: '0 0 * * *' }]   # 08:00 HKT
  workflow_dispatch:
    inputs:
      hours: { description: 'Lookback hours', default: '26' }
concurrency:
  group: daily-briefing
  cancel-in-progress: false
```

Steps: checkout → setup-python 3.12 → `astral-sh/setup-uv` → `uv sync` → copy `data/config.personal.json` to `data/config.json` → `uv run horizon --hours ${{ inputs.hours || 26 }}` (which writes `web/data.json` and the archive) → `peaceiris/actions-gh-pages@v4` with `publish_dir: ./web`, `keep_files: true`, `publish_branch: gh-pages`, `enable_jekyll: false`.

Permissions: `contents: write`. The LLM key is needed by exactly one step.

Secrets: `OPENAI_API_KEY` / `GOOGLE_API_KEY` (one required), `APIFY_TOKEN` (optional).

`.github/workflows/deploy-docs.yml` is renamed to `.disabled` in the same change, otherwise any `docs/**` push republishes the Jekyll site over `index.html` on `gh-pages` and races the daily run.

Pages is configured to serve the `gh-pages` branch, root, not "GitHub Actions".

## 16. Module layout (new files)

```
horizon_site/
  __init__.py
  overview.py         # 3 × group executive summary
  publish.py          # enriched items + views → data.json + archive
  models.py           # SitePayload dataclasses (serialisation only)
tests/test_site_publish.py
tests/test_overview.py
tests/test_zh_hant.py
web/index.html
web/assets/app.js
web/assets/style.css
web/data.sample.json
profiles/fashion/*
profiles/ai-news/*
profiles/energy-data/*
data/config.personal.json
.github/workflows/daily_update.yml
.github/workflows/deploy-docs.yml.disabled
```

Edits (small, guarded):
- `src/orchestrator.py` — after filtering: generate overviews, then call `horizon_site.publish`
- `src/ai/summarizer.py` — `zh-Hant` labels, optional overview rendering
- `src/ai/prompting/enrichment.py` — language names
- `src/ai/localization.py` — `s2t` guard
- `pyproject.toml` — include `horizon_site` package
- `README.md` — replace with personal setup notes (documented as intentional divergence)

Note: `data/summaries/*.md` and `docs/_posts/*.md` remain gitignored; the `gh-pages` branch is the archive of record.

## 17. Failure behaviour

- A scraper failure is isolated by upstream `FetchResult.collect`; the run continues and reports it in `failures`.
- Missing LLM key or auth error → run fails loudly, no deploy; the previous day's page stays live.
- Enrichment failure for one item → item dropped with a logged warning, counted in the run log.
- Traditional-Chinese guard failure → the run fails rather than publishing Simplified.
- Publish failure → the run fails before the deploy step, so `gh-pages` keeps the last good build.
- No items at all → publish an empty-state page for all three groups; never delete the archive.

## 18. Testing

- `pytest` unit tests for `horizon_site.publish`: payload shape, all three groups present, `status` transitions, empty groups, missing fields, archive write.
- `test_overview.py`: stub AI client; overview ≤120 chars, empty string on failure, no exception propagates.
- `test_zh_hant.py`: Simplified input fixture is converted; a real output sample has no Simplified-only characters.
- `web/data.sample.json` is committed so the front-end can be reviewed with `python -m http.server` in `web/` without a run.
- Manual acceptance: one `workflow_dispatch` with default hours, then confirm the page renders, the three tabs are present, and `gh-pages` has `data.json` + `archive/<today>.json`. The archive builds up over subsequent days; there is no backfill.

## 19. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Gemini unavailable from HK / quota exceeded | Provider is one config field; document OpenRouter + DeepSeek. Fail loudly on auth errors. |
| RSS source blocks GitHub runner IP | Per-source failure isolation; `failures` shown in UI; swap URL in config only. |
| Upstream refactor breaks edits | New code lives in `horizon_site/`; five small upstream files touched. |
| `deploy-docs.yml` overwrites the site | Disabled in the same change; single concurrency group. |
| Model outputs Simplified | `s2t` guard + explicit prompt + failing test. |
| Free-tier quota blowout | `max_items: 18`, enrichment only on selected items, 3 overview calls, one run per day. |
| Cron drift | `--hours 26`; documented as approximate. |
| Fork has Actions disabled | Setup checklist must enable workflows on the fork. |

## 20. Builder-check resolutions

The seven questions raised by the design review, and how this document settles them:

1. **State across the publisher boundary** — publish in-process at the end of `HorizonOrchestrator.run()`; no intermediate file, one workflow step, one secret. Overviews also live in the run (orchestrator), because `DailySummarizer` has no client.
2. **Category vs profile grouping** — `group_by: "category"`, ids `fashion`/`ai`/`natgas`, every source pinned. Chinese tab names live in `category_groups.<id>.name`.
3. **Google News** — two plain `sources.rss` entries; redirect links and the 48 h query window accepted, dedup by URL.
4. **Archive semantics** — one file per run date, no bucketing, no backfill; `--hours` only changes how much a single run looks back.
5. **`data_points`** — optional block; items survive without numbers; UI hides an empty list.
6. **Empty vs failed category** — all three groups are always emitted; `status` + `note` distinguish "no news" from "sources down"; `failures` is fetch-only and excludes disabled sources.
7. **`deploy-docs.yml`** — disabled; `gh-pages` is owned by the daily workflow alone; Pages serves the branch.

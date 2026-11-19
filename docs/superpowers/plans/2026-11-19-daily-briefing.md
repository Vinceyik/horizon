# Personal Daily Briefing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the Horizon fork into a personal Traditional-Chinese daily briefing covering fashion, AI, and natural gas, published to GitHub Pages by a daily GitHub Action.

**Architecture:** Horizon's existing pipeline (scrape → classify → score → filter → enrich) is kept unchanged. Three new profiles and a personal config drive the editorial layer; a new `src/site/` package turns the run's in-memory items into `web/data.json` plus a per-day archive; a hand-written static front-end reads that JSON. The run publishes in-process, so there is one workflow step and one secret.

**Tech Stack:** Python 3.12, uv, Horizon (`src/`), pytest, vanilla HTML/CSS/JS, GitHub Actions, GitHub Pages.

**Spec:** `docs/superpowers/specs/2026-11-19-daily-briefing-design.md`

## Global Constraints

- Python `>=3.11`; CI uses 3.12. Use `uv`, never a hand-made virtualenv.
- New Python code lives in `src/site/` so it is covered by `[tool.hatch.build.targets.wheel] packages = ["src"]`. Do not add a top-level package and do not edit `pyproject.toml` packaging.
- Output language tag is exactly `zh-Hant`. No Simplified-only character may reach `web/data.json`.
- `digest.group_by` is `"profile"`. Group ids are exactly `fashion`, `ai`, `natgas`.
- `max_items: 18`; thresholds `fashion: 6.5`, `ai-news: 6.5`, `energy-data: 5.5`.
- No new runtime dependencies. `opencc` is already available via `opencc-python-reimplemented`.
- Site output directory is `web/`. Deploy target is the `gh-pages` branch, root, `keep_files: true`, Jekyll disabled.
- Enrichment block ids are exactly `summary` (primary), `blurb`, `data_points`. `data_points` is `optional: true`.
- Every commit is conventional-commit style and must not modify files outside its task's file list.

## Review Focus

Inputs and conditions the spec implies but no happy-path test covers. Each line's test is attached to the task that owns the code.

1. **A run that finds nothing** (quiet day, or every fetch empty) — the site must still publish a payload with all three groups marked `empty`, and must not delete yesterday's archive. (Task 5)
2. **An item missing its `blurb` or `data_points` block** (optional block skipped, or older item) — the page renders with the summary alone; no `KeyError`, no empty string in the URL. (Task 3)
3. **Model returns Simplified Chinese** despite the prompt — it is converted before writing, never published raw. (Task 1 and Task 3)
4. **`gh-pages` already holds yesterday's files plus the old Jekyll site** — the deploy keeps the archive and does not resurrect `index.md`. (Task 9)
5. **A title or blurb containing `&`, `<`, or an unescaped quote** — JSON stays valid and the rendered link opens the original article. (Task 8)

---

### Task 1: `zh-Hant` language plumbing

**Files:**
- Modify: `src/ai/localization.py:1-14`
- Modify: `src/ai/prompting/enrichment.py:20-23`
- Modify: `src/ai/summarizer.py:50-91`
- Modify: `profiles/tech-news/profile.json`, `profiles/tech-blog/profile.json`, `profiles/finance-news/profile.json`, `profiles/ai-creator/profile.json` (`display_names`)
- Test: `tests/test_zh_hant.py`

**Interfaces:**
- Produces: `normalize_language(text: str, language: str) -> str` — `"zh"` → Simplified, `"zh-Hant"` → Traditional, anything else unchanged.
- Produces: `target_language_instruction(language: str) -> str` — returns a phrase naming the language, used inside enrichment prompts.
- Produces: `LABELS["zh-Hant"]` with the same keys as `LABELS["zh"]`.

- [ ] **Step 1: Prepare the environment**

Run:
```bash
python -m pip install uv
uv sync --extra dev
uv run pytest tests -q
```
Expected: the existing suite passes. Record the count; it is the baseline.

- [ ] **Step 2: Create the branch**

```bash
git checkout -b personal/briefing
```

- [ ] **Step 3: Write the failing test**

```python
# tests/test_zh_hant.py
from src.ai.localization import normalize_language
from src.ai.prompting.enrichment import target_language_instruction
from src.ai.summarizer import LABELS

SIMPLIFIED_SAMPLE = "这个国家发电数据创新高"


def test_zh_hant_converts_simplified_to_traditional():
    assert normalize_language(SIMPLIFIED_SAMPLE, "zh-Hant") == "這個國家發電數據創新高"


def test_zh_hant_leaves_english_and_numbers_alone():
    text = "Henry Hub closed at $3.42, +5.2%"
    assert normalize_language(text, "zh-Hant") == text


def test_zh_still_converts_to_simplified():
    assert normalize_language("這個國家發電數據", "zh") == "这个国家发电数据"


def test_target_language_instruction_names_traditional():
    assert "Traditional Chinese" in target_language_instruction("zh-Hant")


def test_labels_exist_for_zh_hant():
    assert set(LABELS["zh-Hant"]) == set(LABELS["zh"])
```

- [ ] **Step 4: Run it to verify it fails**

Run: `uv run pytest tests/test_zh_hant.py -v`
Expected: FAIL — `KeyError: 'zh-Hant'` or an assertion mismatch.

- [ ] **Step 5: Implement the conversion**

In `src/ai/localization.py`, add a second OpenCC converter and a `zh-Hant` branch in `normalize_language`, keyed on `language.lower() == "zh-hant"`, returning `_SIMPLIFIED_TO_TRADITIONAL.convert(text)`. Leave the `zh` branch and the passthrough untouched.

In `src/ai/prompting/enrichment.py`, extend `target_language_instruction` so `zh-Hant` returns a string containing `"Traditional Chinese (Hong Kong)"` and the tag `zh-Hant`; keep the existing `zh` branch unchanged.

In `src/ai/summarizer.py`, add a `"zh-Hant"` entry to `LABELS` translated from the `"zh"` entry into Traditional Chinese (header `"Horizon 每日速遞"`). Copy the key set exactly.

In each `profiles/*/profile.json`, add `"zh-Hant"` to `display_names` with the Traditional form of the existing `zh` value (`科技新聞`, `技術深入`, `財經新聞`, `AI 創作`).

- [ ] **Step 6: Run the tests**

Run: `uv run pytest tests/test_zh_hant.py -v && uv run pytest tests -q`
Expected: all pass, including the baseline count from Step 1.

- [ ] **Step 7: Commit**

```bash
git add src/ai/localization.py src/ai/prompting/enrichment.py src/ai/summarizer.py profiles tests/test_zh_hant.py
git commit -m "feat(i18n): add zh-Hant output language"
```

---

### Task 2: Site payload models

**Files:**
- Create: `src/site/__init__.py`
- Create: `src/site/models.py`
- Test: `tests/test_site_models.py`

**Interfaces:**
- Produces: `SiteItem`, `SiteGroup`, `SitePayload` frozen dataclasses, each with `to_dict() -> dict`.
- Produces: `GroupStatus = Literal["ok", "empty", "failed"]`.
- JSON keys are fixed: `generatedAt`, `totalFetched`, `originalTitle`, `dataPoints`, `publishedAt`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_site_models.py
import json

from src.site.models import SiteGroup, SiteItem, SitePayload


def _item():
    return SiteItem(
        title="勞力士發布新款",
        original_title="Rolex unveils new model",
        url="https://example.com/a?x=1&y=2",
        source="Hodinkee",
        score=8.0,
        blurb="新款潛水錶加入鈦金屬錶殼",
        summary="完整摘要",
        data_points=["定價 12,000 美元（較上代 +4%）"],
        published_at="2026-11-18T22:10:00Z",
    )


def test_payload_uses_camel_case_keys():
    payload = SitePayload(
        generated_at="2026-11-19T08:12:31+08:00",
        date="2026-11-19",
        language="zh-Hant",
        total_fetched=214,
        selected=1,
        groups=[SiteGroup(id="fashion", name="時尚與精品", overview="重點", status="ok", note=None, items=[_item()])],
        failures=[{"source": "twitter", "reason": "APIFY_TOKEN missing"}],
    )
    data = payload.to_dict()
    assert data["generatedAt"] == "2026-11-19T08:12:31+08:00"
    assert data["totalFetched"] == 214
    assert data["groups"][0]["items"][0]["originalTitle"] == "Rolex unveils new model"
    assert data["groups"][0]["items"][0]["dataPoints"] == ["定價 12,000 美元（較上代 +4%）"]


def test_payload_is_json_serialisable_with_special_characters():
    payload = SitePayload(
        generated_at="2026-11-19T08:00:00+08:00",
        date="2026-11-19",
        language="zh-Hant",
        total_fetched=1,
        selected=1,
        groups=[SiteGroup(id="ai", name="AI 前沿", overview="", status="ok", note=None,
                          items=[_item()])],
        failures=[],
    )
    encoded = json.dumps(payload.to_dict(), ensure_ascii=False)
    assert '"https://example.com/a?x=1&y=2"' in encoded
    assert json.loads(encoded)["groups"][0]["id"] == "ai"


def test_empty_group_survives_serialisation():
    payload = SitePayload(
        generated_at="2026-11-19T08:00:00+08:00", date="2026-11-19", language="zh-Hant",
        total_fetched=0, selected=0,
        groups=[SiteGroup(id="natgas", name="天然氣數據", overview="", status="empty",
                          note="今日無新內容", items=[])],
        failures=[],
    )
    group = payload.to_dict()["groups"][0]
    assert group["status"] == "empty"
    assert group["items"] == []
    assert group["note"] == "今日無新內容"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_site_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.site'`.

- [ ] **Step 3: Implement the dataclasses**

`src/site/__init__.py` stays empty. In `src/site/models.py`, define the three frozen dataclasses with the field names given in the test, `list` defaults via `field(default_factory=list)`, and `to_dict()` methods that emit the camelCase keys. `score` is `Optional[float]`. Do not add `asdict` shortcuts — the key names differ.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_site_models.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/site tests/test_site_models.py
git commit -m "feat(site): add payload models"
```

---

### Task 3: Payload builder and writer

**Files:**
- Create: `src/site/publish.py`
- Test: `tests/test_site_publish.py`

**Interfaces:**
- Consumes: `SiteItem`, `SiteGroup`, `SitePayload` from Task 2; `ContentItem`, `ContentBlock` from `src.models`.
- Produces:
  - `item_group_id(item: ContentItem, profile_to_group: dict[str, str], default_group: str) -> str`
  - `source_label(item: ContentItem) -> str`
  - `parse_data_points(content: str) -> list[str]`
  - `item_to_site_item(item: ContentItem, language: str) -> SiteItem`
  - `build_payload(*, items, groups: list[tuple[str, str, list[str]]], overviews: dict[str, str], failures: list[dict], group_failed: dict[str, bool], total_fetched: int, language: str, now: datetime) -> SitePayload`
  - `write_payload(payload: SitePayload, web_dir: Path) -> tuple[Path, Path]` — returns `(latest_path, archive_path)`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_site_publish.py
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.models import (ContentAnalysis, ContentArtifact, ContentBlock, ContentItem,
                        ProcessingResult, ClassificationResult, SourceType)
from src.site.publish import (build_payload, item_group_id, item_to_site_item,
                              parse_data_points, source_label, write_payload)


def make_item(profile="fashion", lang="zh-Hant", blocks=None, category=None):
    item = ContentItem(
        id="rss:fashion:1",
        source_type=SourceType.RSS,
        title="Original English title",
        url="https://example.com/watch?utm=1&x=2",
        published_at=datetime(2026, 11, 18, 22, 10, tzinfo=timezone.utc),
        metadata={"feed_name": "Hodinkee", "category": category},
        profile=profile,
    )
    item.processing = ProcessingResult(
        classification=ClassificationResult(profile=profile, method="source_override"),
        analysis=ContentAnalysis(score=8.0, reason="r", summary="fallback"),
        artifacts={
            lang: ContentArtifact(
                language=lang,
                title="勞力士新款",
                blocks=blocks if blocks is not None else [
                    ContentBlock(id="summary", title="摘要", content="完整摘要", primary=True),
                    ContentBlock(id="blurb", title="短評", content="鈦金屬錶殼"),
                    ContentBlock(id="data_points", title="數據", content="- 定價 12,000 美元（較上代 +4%）\n- 直徑 41mm"),
                ],
            )
        },
    )
    return item


def test_item_group_id_uses_profile():
    assert item_group_id(make_item(), {"fashion": "fashion"}, "other") == "fashion"


def test_item_group_id_falls_back_when_profile_unknown():
    item = make_item(profile="tech-news")
    assert item_group_id(item, {"fashion": "fashion"}, "other") == "other"


def test_source_label_prefers_feed_name():
    assert source_label(make_item()) == "Hodinkee"


def test_source_label_falls_back_to_source_type():
    item = make_item()
    item.metadata = {}
    assert source_label(item) == "rss"


def test_parse_data_points_strips_bullets_and_blanks():
    content = "- 庫存 +52 BCF（vs 五年均值 +18）\n\n* 出口 15.1 Bcf/d\n"
    assert parse_data_points(content) == ["庫存 +52 BCF（vs 五年均值 +18）", "出口 15.1 Bcf/d"]


def test_item_without_blurb_still_builds():
    item = make_item(blocks=[ContentBlock(id="summary", title="摘要", content="完整摘要", primary=True)])
    site_item = item_to_site_item(item, "zh-Hant")
    assert site_item.blurb == ""
    assert site_item.data_points == []
    assert site_item.summary == "完整摘要"


def test_item_without_artifact_falls_back_to_original_title():
    item = make_item()
    item.processing.artifacts = {}
    site_item = item_to_site_item(item, "zh-Hant")
    assert site_item.title == "Original English title"
    assert site_item.summary == "fallback"


def test_simplified_text_is_converted_before_publishing():
    item = make_item(blocks=[
        ContentBlock(id="summary", title="摘要", content="这个国家发电数据创新高", primary=True),
        ContentBlock(id="blurb", title="短評", content="库存下降"),
    ])
    site_item = item_to_site_item(item, "zh-Hant")
    assert site_item.summary == "這個國家發電數據創新高"
    assert site_item.blurb == "庫存下降"


def test_build_payload_emits_all_groups_even_when_empty():
    payload = build_payload(
        items=[make_item()],
        groups=[("fashion", "時尚與精品", ["fashion"]), ("ai", "AI 前沿", ["ai-news"]),
                ("natgas", "天然氣數據", ["energy-data"])],
        overviews={"fashion": "今日重點"},
        failures=[{"source": "twitter", "reason": "missing token"}],
        group_failed={"natgas": True},
        total_fetched=120,
        language="zh-Hant",
        now=datetime(2026, 11, 19, 0, 12, 31, tzinfo=timezone.utc),
    )
    by_id = {g.id: g for g in payload.groups}
    assert by_id["fashion"].status == "ok" and len(by_id["fashion"].items) == 1
    assert by_id["fashion"].overview == "今日重點"
    assert by_id["ai"].status == "empty" and by_id["ai"].note == "今日無新內容"
    assert by_id["natgas"].status == "failed"
    assert payload.selected == 1
    assert payload.generated_at.endswith("+08:00")


def test_write_payload_creates_latest_and_archive(tmp_path: Path):
    payload = build_payload(
        items=[], groups=[("fashion", "時尚與精品", ["fashion"])], overviews={},
        failures=[], group_failed={}, total_fetched=0, language="zh-Hant",
        now=datetime(2026, 11, 19, 0, 0, tzinfo=timezone.utc),
    )
    latest, archive = write_payload(payload, tmp_path)
    assert latest == tmp_path / "data.json"
    assert archive == tmp_path / "archive" / "2026-11-19.json"
    assert latest.read_text(encoding="utf-8") == archive.read_text(encoding="utf-8")
    assert '"fashion"' in latest.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_site_publish.py -v`
Expected: FAIL — `ModuleNotFoundError` / import errors.

- [ ] **Step 3: Implement `src/site/publish.py`**

Rules the tests do not spell out:
- `item_to_site_item` reads `item.processing.artifacts.get(language)`. Title = artifact title when present, else `item.title`. `original_title` is always `item.title`. `url` is `str(item.url)`.
- Every text field (`title`, `summary`, `blurb`, each data point) is passed through `normalize_language(text, language)` from `src.ai.localization` before being stored, so a Simplified slip cannot reach `data.json`.
- `summary` = the block with `primary=True`, else the block whose id is `summary`, else `item.processing.analysis.summary`, else `""`.
- `blurb` = the block with id `blurb`, else `""`.
- `data_points` = `parse_data_points` on the block with id `data_points`, else `[]`. `parse_data_points` strips leading `-`, `*`, `•` plus surrounding whitespace, drops empty lines, and keeps order.
- `score` = `item.processing.analysis.score` when an analysis exists, else `None`.
- `build_payload` filters `items` into groups by `item_group_id`; group order follows the `groups` argument; items within a group keep input order (already score-sorted upstream).
- `status` per group: `"ok"` when it has items; `"failed"` when `group_failed.get(gid)` is true and it has none; else `"empty"`.
- `note` is `None` for `ok`, `"今日無新內容"` for `empty`, `"來源暫時無法讀取"` for `failed`.
- `generated_at` = `now.astimezone(timezone(timedelta(hours=8))).isoformat(timespec="seconds")`.
- `date` = `payload.date` from `now` in +08:00, `YYYY-MM-DD`.
- `selected` = `len(items)`; `total_fetched` is passed through.
- `write_payload` creates `web_dir` and `web_dir/archive`, writes `data.json` and `archive/<date>.json` with `json.dumps(..., ensure_ascii=False, indent=2)`, and returns both paths.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_site_publish.py -v`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add src/site/publish.py tests/test_site_publish.py
git commit -m "feat(site): build and write daily payload"
```

---

### Task 4: Per-group executive summaries

**Files:**
- Create: `src/site/overview.py`
- Test: `tests/test_overview.py`

**Interfaces:**
- Consumes: `AIClient.complete(system, user, temperature=None, max_tokens=None) -> str` from `src.ai.client`; `ContentItem` from `src.models`.
- Produces: `async generate_group_overviews(client, groups: list[tuple[str, str, list[ContentItem]]], language: str) -> dict[str, str]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_overview.py
import asyncio

from src.site.overview import generate_group_overviews


class FakeClient:
    def __init__(self, reply="今日重點是新品與庫存。", raise_for=None):
        self.reply = reply
        self.raise_for = raise_for
        self.calls = []

    async def complete(self, system, user, temperature=None, max_tokens=None):
        self.calls.append((system, user))
        if self.raise_for and self.raise_for in user:
            raise RuntimeError("boom")
        return self.reply


def run(coro):
    return asyncio.run(coro)


def test_generates_one_overview_per_group():
    client = FakeClient()
    groups = [("fashion", "時尚與精品", []), ("ai", "AI 前沿", [])]
    result = run(generate_group_overviews(client, groups, "zh-Hant"))
    assert set(result) == {"fashion", "ai"}
    assert len(client.calls) == 2


def test_failed_group_yields_empty_string_not_exception():
    client = FakeClient(raise_for="AI 前沿")
    result = run(generate_group_overviews(client, [("ai", "AI 前沿", [])], "zh-Hant"))
    assert result == {"ai": ""}


def test_overview_is_capped_at_120_characters():
    client = FakeClient(reply="重" * 300)
    result = run(generate_group_overviews(client, [("fashion", "時尚與精品", [])], "zh-Hant"))
    assert len(result["fashion"]) <= 120


def test_prompt_forbids_simplified_chinese():
    client = FakeClient()
    run(generate_group_overviews(client, [("fashion", "時尚與精品", [])], "zh-Hant"))
    system, user = client.calls[0]
    assert "Traditional Chinese" in system + user
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_overview.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `src/site/overview.py`**

`generate_group_overviews` loops over groups sequentially. For each group it builds a user prompt from the group name and up to 12 items (`title` + primary block summary, each truncated to 200 characters, total prompt capped at 4000 characters), calls `client.complete(system=..., user=..., temperature=0.3, max_tokens=300)`, strips the reply, truncates to 120 characters at a sentence boundary when possible, and stores `""` on any exception. The system prompt states: Traditional Chinese (Hong Kong), 2–3 sentences, no bullets, no headline restatement, no marketing language. Empty groups return `""` without an API call.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_overview.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/site/overview.py tests/test_overview.py
git commit -m "feat(site): generate per-group executive summaries"
```

---

### Task 5: Wire publishing into the run

**Files:**
- Modify: `src/orchestrator.py:1-40` (imports), `:296-306` (after filtering), `:398-410` (end of run), `:279-281` (empty-early-return)
- Test: `tests/test_site_wiring.py`

**Interfaces:**
- Consumes: `generate_group_overviews` (Task 4), `build_payload`, `write_payload`, `item_group_id` (Task 3).
- Produces: `src.site.publish.site_groups(config, items) -> list[tuple[str, str, list[ContentItem]]]` and `src.site.publish.profile_to_group_map(config) -> dict[str, str]` (both pure, tested here), plus a `HorizonOrchestrator._publish_site(...)` method.
- Env override: `HORIZON_SITE_DIR` (default `web`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_site_wiring.py
from src.site.publish import profile_to_group_map, site_groups


class FakeGroup:
    def __init__(self, name, categories):
        self.name = name
        self.categories = categories


class FakeDigest:
    def __init__(self, groups):
        self.category_groups = groups
        self.default_group = "other"


class FakeConfig:
    def __init__(self, groups):
        self.digest = FakeDigest(groups)


def test_profile_to_group_map_is_reversible():
    config = FakeConfig({
        "fashion": FakeGroup("時尚與精品", ["fashion"]),
        "ai": FakeGroup("AI 前沿", ["ai-news"]),
        "natgas": FakeGroup("天然氣數據", ["energy-data"]),
    })
    assert profile_to_group_map(config) == {
        "fashion": "fashion", "ai-news": "ai", "energy-data": "natgas",
    }


def test_site_groups_keeps_config_order_and_names():
    config = FakeConfig({
        "fashion": FakeGroup("時尚與精品", ["fashion"]),
        "ai": FakeGroup("", ["ai-news"]),
    })
    groups = site_groups(config, [])
    assert [g[0] for g in groups] == ["fashion", "ai"]
    assert groups[1][1] == "ai"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_site_wiring.py -v`
Expected: FAIL — `ImportError: cannot import name 'profile_to_group_map'`.

- [ ] **Step 3: Add the helpers to `src/site/publish.py`**

`profile_to_group_map(config)` iterates `config.digest.category_groups.items()` and maps every entry of `group.categories` to the group id. `site_groups(config, items)` returns `[(gid, group.name or gid, list(group.categories))]` in config order.

- [ ] **Step 4: Run the helper tests**

Run: `uv run pytest tests/test_site_wiring.py -v`
Expected: 2 passed.

- [ ] **Step 5: Wire the orchestrator**

In `HorizonOrchestrator.run()`:
1. Replace the `if not all_items: ... return` block with a call to `await self._publish_site([], total_fetched=0, report=None)` followed by the existing `return`.
2. Immediately after `important_items = filtering_result.items`, compute `groups = site_groups(self.config, important_items)` and `overviews = await generate_group_overviews(self.ai_client, groups, language)` where `language = self.config.ai.languages[0]`. Wrap the overview call so an exception leaves `overviews = {}`.
3. After the per-language summary loop, call `await self._publish_site(important_items, total_fetched=len(all_items), report=self.last_fetch_report, overviews=overviews, groups=groups, language=language)`.

`_publish_site(self, items: list[ContentItem], *, total_fetched: int, report: Optional[FetchReport], overviews: Optional[dict[str, str]] = None, groups=None, language: Optional[str] = None) -> None` builds `group_failed` from `report.outcomes` and the RSS config (a group is failed when every RSS source whose `profile` maps into it has a non-success outcome), calls `build_payload`, then `write_payload(payload, Path(os.environ.get("HORIZON_SITE_DIR", "web")))`, and prints the two written paths with `self.console`. When `groups` is `None` it calls `site_groups(self.config, items)`; when `language` is `None` it uses `self.config.ai.languages[0]`. Add `import os` to the module imports if absent.

- [ ] **Step 6: Write the empty-run regression test**

```python
# append to tests/test_site_wiring.py
from datetime import datetime, timezone
from src.site.publish import build_payload


def test_empty_run_still_publishes_three_groups():
    config = FakeConfig({
        "fashion": FakeGroup("時尚與精品", ["fashion"]),
        "ai": FakeGroup("AI 前沿", ["ai-news"]),
        "natgas": FakeGroup("天然氣數據", ["energy-data"]),
    })
    payload = build_payload(
        items=[], groups=site_groups(config, []), overviews={}, failures=[],
        group_failed={}, total_fetched=0, language="zh-Hant",
        now=datetime(2026, 11, 19, 0, 0, tzinfo=timezone.utc),
    )
    assert [g.status for g in payload.groups] == ["empty", "empty", "empty"]
```

- [ ] **Step 7: Run the full suite**

Run: `uv run pytest tests -q`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add src/orchestrator.py src/site/publish.py tests/test_site_wiring.py
git commit -m "feat: publish site payload at the end of each run"
```

---

### Task 6: Three editorial profiles

**Files:**
- Create: `profiles/fashion/{profile.json,match.md,analysis.md,enrichment.md}`
- Create: `profiles/ai-news/{profile.json,match.md,analysis.md,enrichment.md}`
- Create: `profiles/energy-data/{profile.json,match.md,analysis.md,enrichment.md}`
- Test: `tests/test_profiles_personal.py`

**Interfaces:**
- Produces: profiles with ids `fashion`, `ai-news`, `energy-data`, each with `display_names["zh-Hant"]` and blocks `summary` (primary), `blurb`, `data_points` (optional).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_profiles_personal.py
from pathlib import Path

from src.processing.profiles import ProfileRegistry

EXPECTED = {
    "fashion": "時尚與精品",
    "ai-news": "AI 前沿",
    "energy-data": "天然氣數據",
}


def test_personal_profiles_load_and_expose_required_blocks():
    registry = ProfileRegistry.load(Path("profiles"), "fashion")
    for profile_id, display in EXPECTED.items():
        profile = registry.get(profile_id)
        assert profile.definition.display_names["zh-Hant"] == display
        ids = [b.id for b in profile.definition.enrichment.blocks]
        assert ids == ["summary", "blurb", "data_points"]
        assert profile.definition.enrichment.blocks[0].primary is True
        assert profile.definition.enrichment.blocks[2].optional is True
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_profiles_personal.py -v`
Expected: FAIL — profile not found.

- [ ] **Step 3: Write the profiles**

Mirror `profiles/finance-news/` exactly in structure (`profile.json` keys: `id`, `name`, `display_names`, `match`, `analysis`, `enrichment`). Content rules:

- `fashion` — match: watches, apparel, jewellery, auctions, collaborations, product launches. analysis rubric: 9–10 collection-defining launch, major auction record, brand-level strategic shift; 7–8 notable release or collaboration with concrete detail; 5–6 routine drop or trend piece with specifics; 3–4 press release, celebrity styling, listicle, affiliate round-up; 0–2 pure marketing, resale hype without data. enrichment: `summary` (3–5 sentences, facts first), `blurb` ("30 個中文字以內，講出重點，不要重複標題"), `data_points` (auction prices, release dates, materials, prices, all with a comparison).
- `ai-news` — match: model releases, API/SDK changes, open-source tooling, benchmarks, concrete policy. analysis: reject funding-only news, "AI will change everything" opinion, webinar ads, benchmark charts without baselines. Same three blocks; `blurb` emphasises what changed and for whom.
- `energy-data` — match: US storage, Henry Hub/TTF/JKM, LNG flows, HDD/CDD, pipeline capacity. analysis: 9–10 a figure that changes the balance with a clear baseline; 7–8 concrete data with comparison; 5–6 single data point with context; 3–4 "surged/plunged" without numbers; 0–2 price commentary with no figure. enrichment: `summary` must lead with the number; `blurb` ≤30 characters; `data_points` instructs "每一行一個數據，格式 `項目: 數值（變化）`，至少兩個".

All three `enrichment.md` files must contain the sentence `Use Traditional Chinese (Hong Kong). Never output Simplified Chinese characters.`

- [ ] **Step 4: Run the test**

Run: `uv run pytest tests/test_profiles_personal.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add profiles tests/test_profiles_personal.py
git commit -m "feat(profiles): add fashion, ai-news, energy-data"
```

---

### Task 7: Personal configuration

**Files:**
- Create: `data/config.personal.json`
- Test: `tests/test_config_personal.py`

**Interfaces:**
- Consumes: profile ids from Task 6; group ids `fashion`, `ai`, `natgas`; language `zh-Hant`.
- Produces: a config that `src.models.Config` validates and whose `digest.group_by` is `"profile"`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config_personal.py
import json
from pathlib import Path

from src.models import Config


def test_personal_config_is_valid():
    data = json.loads(Path("data/config.personal.json").read_text(encoding="utf-8"))
    config = Config(**data)
    assert config.ai.languages == ["zh-Hant"]
    assert config.digest.group_by == "profile"
    assert config.digest.max_items == 18
    assert set(config.digest.category_groups) == {"fashion", "ai", "natgas"}
    assert config.digest.category_groups["ai"].categories == ["ai-news"]
    assert config.processing.profile_settings["energy-data"].threshold == 5.5


def test_every_enabled_source_is_pinned_to_a_personal_profile():
    data = json.loads(Path("data/config.personal.json").read_text(encoding="utf-8"))
    allowed = {"fashion", "ai-news", "energy-data"}
    for feed in data["sources"]["rss"]:
        if feed.get("enabled"):
            assert feed["profile"] in allowed, feed["name"]
    for source in data["sources"].get("github", []):
        if source.get("enabled"):
            assert source["profile"] in allowed
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_config_personal.py -v`
Expected: FAIL — file not found.

- [ ] **Step 3: Write `data/config.personal.json`**

Start from `data/config.github.json` and change:
- `ai`: provider `openai`, model `gpt-4o-mini`, `base_url` `"https://openrouter.ai/api/v1"`, `api_key_env` `"OPENAI_API_KEY"`, `languages: ["zh-Hant"]`, `max_tokens: 8192`, `analysis_concurrency: 3`, `enrichment_concurrency: 3`, `throttle_sec: 0.5`.
- `processing.default_profile`: `"ai-news"`; `profile_settings` exactly `{"fashion": {"threshold": 6.5, "topic_dedup": true}, "ai-news": {"threshold": 6.5, "topic_dedup": true}, "energy-data": {"threshold": 5.5, "topic_dedup": true}}`.
- `sources.rss`: the nine feeds from spec §9 with `enabled: true`, plus Anthropic and the natural-gas Google News query. Each entry carries `name`, `url`, `category` equal to the group id, `profile`, and `content_extractor: "trafilatura"` for publisher sites (omit for Google News).
- `sources.hackernews`: `enabled: true`, `fetch_top_stories: 30`, `min_score: 150`, `profile: "ai-news"`.
- `sources.github`: `enabled: true` with `type: repo_releases` for `vllm-project/vllm` and `sgl-project/sglang`, `profile: "ai-news"`.
- `sources.twitter`: `enabled: false`, `users: []`.
- `digest`: `max_items: 18`, `group_by: "profile"`, `profile_order: ["fashion", "ai-news", "energy-data"]`, `category_groups` exactly:
  `{"fashion": {"name": "時尚與精品", "limit": 5, "categories": ["fashion"]}, "ai": {"name": "AI 前沿", "limit": 6, "categories": ["ai-news"]}, "natgas": {"name": "天然氣數據", "limit": 5, "categories": ["energy-data"]}}`, `default_group: "other"`, `default_group_limit: 2`.
- `collection.time_window_hours`: `26`.
- Remove `email`, `webhook`, `wechat` blocks entirely.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_config_personal.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add data/config.personal.json tests/test_config_personal.py
git commit -m "feat(config): add personal briefing configuration"
```

---

### Task 8: Front-end

**Files:**
- Create: `web/index.html`
- Create: `web/assets/style.css`
- Create: `web/assets/app.js`
- Create: `web/data.sample.json`
- Modify: `.gitignore` (add `web/data.json` and `web/archive/`)

**Interfaces:**
- Consumes: the `data.json` contract from Task 3 (keys exactly as defined there).
- Produces: a static page that renders three tabs from `data.groups`, with no build step.

- [ ] **Step 1: Add the sample payload**

Copy the output shape from `tests/test_site_publish.py::test_build_payload_emits_all_groups_even_when_empty` into `web/data.sample.json`, expanded to three groups with two items each, at least one `dataPoints` list, and one `status: "empty"` group. Include a title containing `&` and a quote to prove escaping.

- [ ] **Step 2: Build the page shell**

`web/index.html` contains: `<header>` with the site title, a `#last-updated` line, a theme toggle `<button id="theme-toggle" aria-label="切換深色模式">`, a `<nav role="tablist" id="tabs">`, `<main id="panels">`, a `<p id="status">` for failures, and `<script src="assets/app.js" defer>`. `<html lang="zh-Hant">`. No external requests, no fonts, no CDN.

- [ ] **Step 3: Build the styles**

`web/assets/style.css` defines light and dark values as custom properties on `:root[data-theme="light"]` and `:root[data-theme="dark"]`, with `@media (prefers-color-scheme: dark)` as the initial hint. Layout: single column, `max-width: 720px`, padding `16px`, tab row that scrolls horizontally on narrow screens, cards with `border-radius: var(--radius)`. Data points render as a tight list with tabular numerals. Include a `:focus-visible` outline on tabs and links.

- [ ] **Step 4: Build the behaviour**

`web/assets/app.js` (ES2020, no dependencies) must:
- read the `theme` key from `localStorage` first, else `prefers-color-scheme`, and set `document.documentElement.dataset.theme`;
- fetch `data.json` (or `?date=YYYY-MM-DD` → `archive/YYYY-MM-DD.json`), render tabs and one panel per group;
- render `status: "empty"` as a muted line and `"failed"` as a warning line inside the panel;
- render `failures` as a single muted line in `#status`;
- write `最後更新` from `generatedAt` using `Intl.DateTimeFormat("zh-HK", {timeZone: "Asia/Hong_Kong", ...})`;
- escape every string inserted into the DOM by using `textContent`/`createElement`, never `innerHTML` with data;
- support arrow-key navigation between tabs and sync `location.hash`;
- probe `archive/` for the previous 13 days with `HEAD` and render a date `<select>` only when at least one exists;
- show a retry button when the fetch fails.

- [ ] **Step 5: Verify manually**

```bash
cd web && python -m http.server 8080
```
Open `http://localhost:8080/?date=2026-11-19` after copying `data.sample.json` to `data.json` and confirm: three tabs, dark toggle persists after reload, `最後更新` shows a Hong Kong time, the item containing `&` renders and links out, the empty group shows its line.

- [ ] **Step 6: Commit**

```bash
git add web .gitignore
git commit -m "feat(web): add static briefing front-end"
```

---

### Task 9: Daily workflow and Pages

**Files:**
- Create: `.github/workflows/daily_update.yml`
- Rename: `.github/workflows/deploy-docs.yml` → `.github/workflows/deploy-docs.yml.disabled`
- Test: `tests/test_workflow_config.py`

**Interfaces:**
- Consumes: `uv run horizon --hours 26`, `data/config.personal.json`, `web/`.
- Produces: a `gh-pages` branch containing `index.html`, `assets/`, `data.json`, `archive/`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_workflow_config.py
from pathlib import Path

WORKFLOW = Path(".github/workflows/daily_update.yml")


def test_daily_workflow_runs_at_hong_kong_8am():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "cron: '0 0 * * *'" in text
    assert "workflow_dispatch" in text


def test_daily_workflow_deploys_only_web():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "publish_dir: ./web" in text
    assert "keep_files: true" in text
    assert "publish_branch: gh-pages" in text
    assert "contents: write" in text
    assert "publish_dir: ./docs" not in text


def test_docs_deploy_workflow_is_disabled():
    assert not Path(".github/workflows/deploy-docs.yml").exists()
    assert Path(".github/workflows/deploy-docs.yml.disabled").exists()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_workflow_config.py -v`
Expected: FAIL — workflow file missing.

- [ ] **Step 3: Write the workflow**

```yaml
name: Daily Briefing

on:
  schedule:
    - cron: '0 0 * * *'   # 08:00 Asia/Hong_Kong
  workflow_dispatch:
    inputs:
      hours:
        description: 'Lookback hours'
        default: '26'

concurrency:
  group: daily-briefing
  cancel-in-progress: false

permissions:
  contents: write

jobs:
  briefing:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: astral-sh/setup-uv@v6
      - run: uv sync
      - name: Use personal config
        run: cp data/config.personal.json data/config.json
      - name: Run Horizon
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
          APIFY_TOKEN: ${{ secrets.APIFY_TOKEN }}
        run: uv run horizon --hours ${{ github.event.inputs.hours || '26' }}
      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v4
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./web
          keep_files: true
          publish_branch: gh-pages
          enable_jekyll: false
          commit_message: "briefing: ${{ github.run_id }}"
```

- [ ] **Step 4: Disable the docs deploy**

```bash
git mv .github/workflows/deploy-docs.yml .github/workflows/deploy-docs.yml.disabled
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest tests/test_workflow_config.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows tests/test_workflow_config.py
git commit -m "ci: add daily briefing workflow and disable docs deploy"
```

---

### Task 10: Setup notes and end-to-end check

**Files:**
- Modify: `README.md`
- Create: `docs/setup.md`

**Interfaces:**
- Consumes: everything above.
- Produces: a checklist a future reader can follow without asking questions.

- [ ] **Step 1: Write `docs/setup.md`**

Cover, in order: fork/push the repo to `Vinceyik/horizon`; enable Actions; add `OPENAI_API_KEY` (OpenRouter) or `GOOGLE_API_KEY` (Gemini) as a repository secret; optional `APIFY_TOKEN`; Settings → Pages → Source `Deploy from a branch` → `gh-pages` / `/`; first manual run via `workflow_dispatch`; where to change sources (only `data/config.personal.json`); the cron drift caveat; the free-tier caveat (Gemini region, OpenRouter limits); and how to revoke the push token.

- [ ] **Step 2: Replace `README.md`**

Title, one-paragraph description, link to `docs/setup.md`, the three tabs, the "built on Thysrael/Horizon (MIT)" credit with a link to the upstream repo, and a note that this fork tracks upstream via `git remote add upstream https://github.com/Thysrael/Horizon.git`.

- [ ] **Step 3: Run the whole suite**

Run: `uv run pytest tests -q`
Expected: all pass.

- [ ] **Step 4: Dry-run the publisher end to end**

Run:
```bash
cp web/data.sample.json web/data.json
cd web && python -m http.server 8080
```
Then open `http://localhost:8080/` and confirm the sample renders. This proves the front-end does not depend on a live run.

- [ ] **Step 5: Commit and push**

```bash
git add README.md docs/setup.md
git commit -m "docs: add personal setup guide"
git push fork personal/briefing
```

- [ ] **Step 6: First real run**

Trigger `Daily Briefing` from the Actions tab with default hours. Confirm: the run completes, `gh-pages` gains `data.json` and `archive/<today>.json`, the Pages URL shows three tabs, and `data.json` contains no Simplified-only characters from the spec's sample set (与 为 国 电 数 发).

---

## Self-review notes

- Spec §9 lists nine feeds; Task 7 config lists them plus the two Google News queries (eleven total). The spec table is the authority for URLs.
- Spec §12 says the overview dict is passed to the summarizer; this plan drops the Markdown rendering of overviews because the Markdown is not published. The payload is the only consumer. This narrows the change and is recorded here deliberately.
- Spec §16 names `horizon_site/`; this plan uses `src/site/` so the existing `packages = ["src"]` hatch config covers it and `pyproject.toml` stays untouched.

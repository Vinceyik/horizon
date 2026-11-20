import asyncio
import json
from datetime import datetime, timezone
from types import SimpleNamespace

from src.models import (AIConfig, CategoryGroupConfig, ClassificationResult,
                        Config, ContentAnalysis, ContentArtifact, ContentBlock,
                        ContentItem, DigestConfig, ProcessingResult,
                        SourceType, SourcesConfig)
from src.orchestrator import HorizonOrchestrator


def make_config() -> Config:
    return Config(
        ai=AIConfig(
            provider="openai",
            model="test",
            api_key_env="TEST_KEY",
            languages=["zh-Hant"],
        ),
        sources=SourcesConfig(),
        digest=DigestConfig(
            category_groups={
                "fashion": CategoryGroupConfig(
                    name="時尚與精品", limit=5, categories=["fashion"]
                ),
                "ai": CategoryGroupConfig(name="AI 前沿", limit=6, categories=["ai-news"]),
                "natgas": CategoryGroupConfig(
                    name="天然氣數據", limit=5, categories=["energy-data"]
                ),
            },
            group_by="profile",
        ),
    )


def make_item(with_artifact: bool) -> ContentItem:
    item = ContentItem(
        id="rss:fashion:1",
        source_type=SourceType.RSS,
        title="Original English title",
        url="https://example.com/a",
        published_at=datetime(2026, 11, 18, tzinfo=timezone.utc),
        metadata={"feed_name": "Hodinkee"},
        profile="fashion",
    )
    artifacts = {}
    if with_artifact:
        artifacts["zh-Hant"] = ContentArtifact(
            language="zh-Hant",
            title="中文標題",
            blocks=[ContentBlock(id="summary", title="摘要", content="中文摘要", primary=True)],
        )
    item.processing = ProcessingResult(
        classification=ClassificationResult(profile="fashion", method="source_override"),
        analysis=ContentAnalysis(score=8.0, reason="r", summary="fallback"),
        artifacts=artifacts,
    )
    return item


def test_quiet_run_publishes_an_empty_page(tmp_path, monkeypatch):
    monkeypatch.setenv("HORIZON_SITE_DIR", str(tmp_path))
    orchestrator = HorizonOrchestrator(make_config(), SimpleNamespace())

    async def fetch(since):
        return []

    orchestrator.fetch_all_sources = fetch
    asyncio.run(orchestrator.run())

    data = json.loads((tmp_path / "data.json").read_text(encoding="utf-8"))
    assert [group["status"] for group in data["groups"]] == ["empty", "empty", "empty"]
    assert (tmp_path / "archive" / (data["date"] + ".json")).exists()


def test_publish_site_drops_items_without_this_language(tmp_path, monkeypatch):
    monkeypatch.setenv("HORIZON_SITE_DIR", str(tmp_path))
    orchestrator = HorizonOrchestrator(make_config(), SimpleNamespace())

    asyncio.run(
        orchestrator._publish_site(
            [make_item(True), make_item(False)],
            total_fetched=2,
            report=None,
            overviews={},
        )
    )

    data = json.loads((tmp_path / "data.json").read_text(encoding="utf-8"))
    assert data["selected"] == 1
    assert [group["status"] for group in data["groups"]] == ["ok", "empty", "empty"]

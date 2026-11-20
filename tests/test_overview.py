import asyncio
from datetime import datetime, timezone

from src.models import (ClassificationResult, ContentAnalysis, ContentArtifact,
                        ContentBlock, ContentItem, ProcessingResult, SourceType)
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


def make_item(title="Rolex launches a titanium Submariner", summary="Rolex 發布鈦金屬潛水錶"):
    item = ContentItem(
        id="rss:fashion:1",
        source_type=SourceType.RSS,
        title=title,
        url="https://example.com/a",
        published_at=datetime(2026, 11, 18, tzinfo=timezone.utc),
    )
    item.processing = ProcessingResult(
        classification=ClassificationResult(profile="fashion", method="source_override"),
        analysis=ContentAnalysis(score=8.0, reason="r", summary=summary),
        artifacts={
            "zh-Hant": ContentArtifact(
                language="zh-Hant",
                title=summary,
                blocks=[ContentBlock(id="summary", title="摘要", content=summary, primary=True)],
            )
        },
    )
    return item


def run(coro):
    return asyncio.run(coro)


def test_generates_one_overview_per_non_empty_group():
    client = FakeClient()
    groups = [("fashion", "時尚與精品", [make_item()]), ("ai", "AI 前沿", [])]
    result = run(generate_group_overviews(client, groups, "zh-Hant"))
    assert set(result) == {"fashion", "ai"}
    assert result["ai"] == ""
    assert len(client.calls) == 1


def test_failed_group_yields_empty_string_not_exception():
    client = FakeClient(raise_for="AI 前沿")
    result = run(generate_group_overviews(client, [("ai", "AI 前沿", [make_item()])], "zh-Hant"))
    assert result == {"ai": ""}


def test_overview_is_capped_at_120_characters():
    client = FakeClient(reply="重" * 300)
    result = run(generate_group_overviews(client, [("fashion", "時尚與精品", [make_item()])], "zh-Hant"))
    assert len(result["fashion"]) <= 120


def test_prompt_forbids_simplified_chinese():
    client = FakeClient()
    run(generate_group_overviews(client, [("fashion", "時尚與精品", [make_item()])], "zh-Hant"))
    system, user = client.calls[0]
    assert "Traditional Chinese" in system + user


def test_throttle_sleeps_between_calls_only(monkeypatch):
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr("src.site.overview._sleep", fake_sleep)
    client = FakeClient()
    groups = [
        ("a", "A", [make_item()]),
        ("b", "B", [make_item()]),
        ("c", "C", [make_item()]),
    ]
    run(generate_group_overviews(client, groups, "zh-Hant", throttle_sec=0.5))
    assert sleeps == [0.5, 0.5]


def test_no_sleep_without_a_throttle(monkeypatch):
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr("src.site.overview._sleep", fake_sleep)
    run(generate_group_overviews(
        FakeClient(), [("a", "A", [make_item()]), ("b", "B", [make_item()])], "zh-Hant"
    ))
    assert sleeps == []

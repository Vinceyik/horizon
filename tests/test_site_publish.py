from datetime import datetime, timezone
from pathlib import Path

from src.models import (ClassificationResult, ContentAnalysis, ContentArtifact,
                        ContentBlock, ContentItem, ProcessingResult, SourceType)
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


def test_parse_data_points_keeps_a_leading_negative_number():
    content = "-52 BCF（市場預期 -60）\n- 出口 15.1 Bcf/d"
    assert parse_data_points(content) == [
        "-52 BCF（市場預期 -60）",
        "出口 15.1 Bcf/d",
    ]


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


def test_original_title_is_converted_too():
    item = make_item()
    item.title = "这个国家发电数据"
    site_item = item_to_site_item(item, "zh-Hant")
    assert site_item.original_title == "這個國家發電數據"


def test_overview_is_converted_at_the_payload_boundary():
    payload = build_payload(
        items=[],
        groups=[("fashion", "時尚與精品", ["fashion"])],
        overviews={"fashion": "这个国家发电数据"},
        failures=[],
        group_failed={},
        total_fetched=0,
        language="zh-Hant",
        now=datetime(2026, 11, 19, 0, 0, tzinfo=timezone.utc),
    )
    assert payload.groups[0].overview == "這個國家發電數據"


def test_items_outside_configured_groups_are_not_published_or_counted():
    payload = build_payload(
        items=[make_item(), make_item(profile="tech-news")],
        groups=[("fashion", "時尚與精品", ["fashion"])],
        overviews={},
        failures=[],
        group_failed={},
        total_fetched=2,
        language="zh-Hant",
        now=datetime(2026, 11, 19, 0, 0, tzinfo=timezone.utc),
    )
    assert payload.selected == 1


def test_write_payload_creates_missing_directories(tmp_path: Path):
    payload = build_payload(
        items=[], groups=[("fashion", "時尚與精品", ["fashion"])], overviews={},
        failures=[], group_failed={}, total_fetched=0, language="zh-Hant",
        now=datetime(2026, 11, 19, 0, 0, tzinfo=timezone.utc),
    )
    latest, archive = write_payload(payload, tmp_path / "deep" / "web")
    assert latest.exists() and archive.exists()


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

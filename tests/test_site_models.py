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

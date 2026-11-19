import json
from pathlib import Path

from src.models import Config


def load_raw():
    return json.loads(Path("data/config.personal.json").read_text(encoding="utf-8"))


def test_personal_config_is_valid():
    config = Config(**load_raw())
    assert config.ai.languages == ["zh-Hant"]
    assert config.digest.group_by == "profile"
    assert config.digest.max_items == 18
    assert set(config.digest.category_groups) == {"fashion", "ai", "natgas"}
    assert config.digest.category_groups["ai"].categories == ["ai-news"]
    assert config.processing.profile_settings["energy-data"].threshold == 5.5


def test_every_enabled_source_is_pinned_to_a_personal_profile():
    data = load_raw()
    allowed = {"fashion", "ai-news", "energy-data"}
    for feed in data["sources"]["rss"]:
        if feed.get("enabled"):
            assert feed["profile"] in allowed, feed["name"]
    for source in data["sources"].get("github", []):
        if source.get("enabled"):
            assert source["profile"] in allowed


def test_delivery_channels_are_off():
    data = load_raw()
    assert data["sources"]["twitter"]["enabled"] is False
    assert data["sources"]["reddit"]["enabled"] is False
    assert data["sources"]["telegram"]["enabled"] is False

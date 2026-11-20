from datetime import datetime, timezone

from src.site.publish import (build_payload, group_failure_map, profile_to_group_map,
                              site_groups)


class FakeGroup:
    def __init__(self, name, categories):
        self.name = name
        self.categories = categories


class FakeDigest:
    def __init__(self, groups):
        self.category_groups = groups
        self.default_group = "other"


class FakeFeed:
    def __init__(self, name, profile, enabled=True):
        self.name = name
        self.profile = profile
        self.enabled = enabled


class FakeScraperSource:
    def __init__(self, profile, enabled=True):
        self.profile = profile
        self.enabled = enabled


class FakeSources:
    def __init__(self, rss, hackernews=None, github=None):
        self.rss = rss
        self.hackernews = hackernews
        self.github = github or []


class FakeConfig:
    def __init__(self, groups, rss=None, hackernews=None, github=None):
        self.digest = FakeDigest(groups)
        self.sources = FakeSources(rss or [], hackernews, github)


def three_groups():
    return {
        "fashion": FakeGroup("時尚與精品", ["fashion"]),
        "ai": FakeGroup("AI 前沿", ["ai-news"]),
        "natgas": FakeGroup("天然氣數據", ["energy-data"]),
    }


def test_profile_to_group_map_is_reversible():
    config = FakeConfig(three_groups())
    assert profile_to_group_map(config) == {
        "fashion": "fashion", "ai-news": "ai", "energy-data": "natgas",
    }


def test_site_groups_keeps_config_order_and_names():
    config = FakeConfig({
        "fashion": FakeGroup("時尚與精品", ["fashion"]),
        "ai": FakeGroup("", ["ai-news"]),
    })
    groups = site_groups(config)
    assert [g[0] for g in groups] == ["fashion", "ai"]
    assert groups[1][1] == "ai"


def test_group_failure_map_marks_only_groups_whose_feeds_all_failed():
    config = FakeConfig(three_groups(), rss=[
        FakeFeed("Hodinkee", "fashion"),
        FakeFeed("Vogue", "fashion"),
        FakeFeed("NGI", "energy-data"),
        FakeFeed("Disabled", "fashion", enabled=False),
    ])
    assert group_failure_map(config, {"Hodinkee"}, set()) == {}
    assert group_failure_map(config, {"Hodinkee", "Vogue"}, set()) == {"fashion": True}
    assert group_failure_map(config, {"NGI"}, set()) == {"natgas": True}
    assert group_failure_map(config, set(), set()) == {}


def test_group_failure_map_counts_hacker_news_and_github():
    config = FakeConfig(
        three_groups(),
        rss=[FakeFeed("Hodinkee", "fashion")],
        hackernews=FakeScraperSource("ai-news"),
        github=[FakeScraperSource("ai-news")],
    )
    assert group_failure_map(config, set(), {"Hacker News"}) == {}
    assert group_failure_map(config, set(), {"Hacker News", "GitHub"}) == {"ai": True}


def test_empty_run_still_publishes_three_groups():
    config = FakeConfig(three_groups())
    payload = build_payload(
        items=[], groups=site_groups(config), overviews={}, failures=[],
        group_failed={}, total_fetched=0, language="zh-Hant",
        now=datetime(2026, 11, 19, 0, 0, tzinfo=timezone.utc),
    )
    assert [g.status for g in payload.groups] == ["empty", "empty", "empty"]

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


def test_personal_profiles_forbid_simplified_output():
    for profile_id in EXPECTED:
        text = Path("profiles", profile_id, "enrichment.md").read_text(encoding="utf-8")
        assert "Traditional Chinese (Hong Kong)" in text
        assert "Never output Simplified Chinese characters" in text

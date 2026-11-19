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

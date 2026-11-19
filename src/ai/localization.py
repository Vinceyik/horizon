"""Deterministic normalization for localized AI output."""

from opencc import OpenCC


_TRADITIONAL_TO_SIMPLIFIED = OpenCC("t2s")
_SIMPLIFIED_TO_TRADITIONAL = OpenCC("s2t")


def normalize_language(text: str, language: str) -> str:
    """Normalize generated text to the script implied by its language tag."""
    normalized = language.lower()
    if normalized == "zh":
        return _TRADITIONAL_TO_SIMPLIFIED.convert(text)
    if normalized == "zh-hant":
        return _SIMPLIFIED_TO_TRADITIONAL.convert(text)
    return text

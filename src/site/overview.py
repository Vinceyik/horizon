"""Generate the per-category executive summary for the daily briefing."""

from __future__ import annotations

import logging
from typing import Optional

from ..ai.localization import normalize_language
from ..models import ContentItem

logger = logging.getLogger(__name__)

MAX_OVERVIEW_CHARS = 120
MAX_ITEMS_IN_PROMPT = 12
MAX_ITEM_LINE_CHARS = 200
MAX_PROMPT_CHARS = 4000

SYSTEM_PROMPT = (
    "You write the executive summary for one section of a personal daily briefing. "
    "Use Traditional Chinese (Hong Kong) only; never output Simplified Chinese characters. "
    "Write 2-3 sentences of plain prose, no bullet points, no headline restatement, "
    "no marketing language. Lead with the single most important development. "
    "Return plain text only."
)


def _item_line(item: ContentItem, language: str) -> str:
    title = item.title
    summary = ""
    if item.processing:
        artifact = item.processing.artifacts.get(language)
        if artifact:
            title = artifact.title or title
            for block in artifact.blocks:
                if block.primary:
                    summary = block.content or ""
                    break
        if not summary and item.processing.analysis:
            summary = item.processing.analysis.summary or ""
    line = f"- {title}: {summary}" if summary else f"- {title}"
    return line[:MAX_ITEM_LINE_CHARS]


def _build_user_prompt(name: str, items: list[ContentItem], language: str) -> str:
    lines = [f"分類：{name}", "", "今日條目："]
    for item in items[:MAX_ITEMS_IN_PROMPT]:
        lines.append(_item_line(item, language))
    prompt = "\n".join(lines)
    return prompt[:MAX_PROMPT_CHARS]


def _trim(text: str) -> str:
    text = text.strip()
    if len(text) <= MAX_OVERVIEW_CHARS:
        return text
    window = text[:MAX_OVERVIEW_CHARS]
    boundary = max(window.rfind(mark) for mark in "。！？")
    if boundary >= MAX_OVERVIEW_CHARS // 2:
        return window[: boundary + 1]
    return window.rstrip()


async def generate_group_overviews(
    client,
    groups: list[tuple[str, str, list[ContentItem]]],
    language: str,
) -> dict[str, str]:
    """Return one 2-3 sentence overview per group, empty string on failure."""
    overviews: dict[str, str] = {}
    for group_id, name, items in groups:
        if not items:
            overviews[group_id] = ""
            continue
        try:
            reply: Optional[str] = await client.complete(
                system=SYSTEM_PROMPT,
                user=_build_user_prompt(name, items, language),
                temperature=0.3,
                max_tokens=300,
            )
            overviews[group_id] = _trim(normalize_language(reply or "", language))
        except Exception:
            logger.warning("Group overview failed for %s", group_id, exc_info=True)
            overviews[group_id] = ""
    return overviews

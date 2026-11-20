"""Build the daily briefing payload and write it to the web directory."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional

from ..ai.localization import normalize_language
from ..models import ContentItem
from .models import GroupStatus, SiteGroup, SiteItem, SitePayload

HKT = timezone(timedelta(hours=8))

SUMMARY_BLOCK = "summary"
BLURB_BLOCK = "blurb"
DATA_BLOCK = "data_points"

GROUP_NOTES: dict[str, Optional[str]] = {
    "ok": None,
    "empty": "今日無新內容",
    "failed": "來源暫時無法讀取",
}

SOURCE_LABEL_KEYS = ("feed_name", "channel", "subreddit", "username", "source_name")

_BULLET_PREFIX = re.compile(r"^\s*[-*\u2022]\s+")


def item_group_id(
    item: ContentItem,
    profile_to_group: dict[str, str],
    default_group: str,
) -> str:
    """Resolve which briefing group an item belongs to."""
    profile = item.processing.classification.profile if item.processing else None
    if isinstance(profile, str):
        return profile_to_group.get(profile, default_group)
    return default_group


def source_label(item: ContentItem) -> str:
    """Human-readable source name, falling back to the source type."""
    metadata = item.metadata or {}
    for key in SOURCE_LABEL_KEYS:
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return item.source_type.value


def parse_data_points(content: str) -> list[str]:
    """Turn a Markdown bullet block into a list of short data lines."""
    points: list[str] = []
    for raw in (content or "").splitlines():
        # Strip only a bullet marker followed by whitespace, so a leading
        # minus sign that belongs to the number survives.
        line = _BULLET_PREFIX.sub("", raw).strip()
        if line:
            points.append(line)
    return points


def _artifact(item: ContentItem, language: str):
    if not item.processing:
        return None
    return item.processing.artifacts.get(language)


def _block_content(item: ContentItem, language: str, block_id: str) -> str:
    artifact = _artifact(item, language)
    if not artifact:
        return ""
    for block in artifact.blocks:
        if block.id == block_id:
            return block.content or ""
    return ""


def _primary_block_content(item: ContentItem, language: str) -> str:
    artifact = _artifact(item, language)
    if not artifact:
        return ""
    for block in artifact.blocks:
        if block.primary:
            return block.content or ""
    return _block_content(item, language, SUMMARY_BLOCK)


def item_to_site_item(item: ContentItem, language: str) -> SiteItem:
    """Flatten one enriched item into the published shape."""
    artifact = _artifact(item, language)
    title = artifact.title if artifact and artifact.title else item.title

    summary = _primary_block_content(item, language)
    if not summary and item.processing and item.processing.analysis:
        summary = item.processing.analysis.summary or ""

    blurb = _block_content(item, language, BLURB_BLOCK)
    raw_points = _block_content(item, language, DATA_BLOCK)

    score = None
    if item.processing and item.processing.analysis:
        score = item.processing.analysis.score

    return SiteItem(
        title=normalize_language(title, language),
        original_title=normalize_language(item.title, language),
        url=str(item.url),
        source=source_label(item),
        score=score,
        blurb=normalize_language(blurb, language),
        summary=normalize_language(summary, language),
        data_points=[normalize_language(point, language) for point in parse_data_points(raw_points)],
        published_at=item.published_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def build_payload(
    *,
    items: Iterable[ContentItem],
    groups: list[tuple[str, str, list[str]]],
    overviews: Optional[dict[str, str]] = None,
    failures: Optional[list[dict]] = None,
    group_failed: Optional[dict[str, bool]] = None,
    total_fetched: int,
    language: str,
    now: datetime,
) -> SitePayload:
    """Assemble the payload, always emitting every configured group."""
    buckets = group_items(items, groups)

    failed = group_failed or {}
    overview_map = overviews or {}

    site_groups: list[SiteGroup] = []
    for group_id, name, _profiles in groups:
        bucket = buckets[group_id]
        if bucket:
            status: GroupStatus = "ok"
        elif failed.get(group_id):
            status = "failed"
        else:
            status = "empty"
        site_groups.append(
            SiteGroup(
                id=group_id,
                name=name,
                overview=normalize_language(overview_map.get(group_id, ""), language),
                status=status,
                note=GROUP_NOTES[status],
                items=[item_to_site_item(item, language) for item in bucket],
            )
        )

    local = now.astimezone(HKT)
    return SitePayload(
        generated_at=local.isoformat(timespec="seconds"),
        date=local.strftime("%Y-%m-%d"),
        language=language,
        total_fetched=total_fetched,
        selected=sum(len(group.items) for group in site_groups),
        groups=site_groups,
        failures=list(failures or []),
    )


def profile_to_group_map(config) -> dict[str, str]:
    """Map every profile id to the briefing group that owns it."""
    mapping: dict[str, str] = {}
    for group_id, group in config.digest.category_groups.items():
        for profile in group.categories:
            mapping[profile] = group_id
    return mapping


def site_groups(config) -> list[tuple[str, str, list[str]]]:
    """Return the configured groups as (id, tab name, profile ids)."""
    return [
        (group_id, group.name or group_id, list(group.categories))
        for group_id, group in config.digest.category_groups.items()
    ]


def group_items(items, groups, default_group: str = "other"):
    """Bucket items into their configured groups, preserving input order."""
    profile_map: dict[str, str] = {}
    for group_id, _name, profiles in groups:
        for profile in profiles:
            profile_map[profile] = group_id
    buckets: dict[str, list] = {group_id: [] for group_id, _n, _p in groups}
    for item in items:
        group_id = item_group_id(item, profile_map, default_group)
        if group_id in buckets:
            buckets[group_id].append(item)
    return buckets


def _sources_by_group(config) -> dict[str, list[tuple[str, str]]]:
    """Map each group to the sources that feed it, as (kind, label) pairs."""
    mapping = profile_to_group_map(config)
    sources: dict[str, list[tuple[str, str]]] = {}

    def add(group_id: str, kind: str, label: str) -> None:
        bucket = sources.setdefault(group_id, [])
        entry = (kind, label)
        if entry not in bucket:
            bucket.append(entry)

    for feed in getattr(config.sources, "rss", None) or []:
        profile = getattr(feed, "profile", None)
        if not feed.enabled or not isinstance(profile, str) or profile == "auto":
            continue
        group_id = mapping.get(profile)
        if group_id:
            add(group_id, "feed", feed.name)

    hackernews = getattr(config.sources, "hackernews", None)
    if hackernews is not None and getattr(hackernews, "enabled", False):
        profile = getattr(hackernews, "profile", None)
        if isinstance(profile, str) and profile != "auto":
            group_id = mapping.get(profile)
            if group_id:
                add(group_id, "scraper", "Hacker News")

    for source in getattr(config.sources, "github", None) or []:
        if not getattr(source, "enabled", False):
            continue
        profile = getattr(source, "profile", None)
        if isinstance(profile, str) and profile != "auto":
            group_id = mapping.get(profile)
            if group_id:
                add(group_id, "scraper", "GitHub")

    return sources


def group_failure_map(config, failed_feeds=(), failed_scrapers=()) -> dict[str, bool]:
    """Mark a group failed only when every source feeding it failed.

    ``failed_feeds`` holds RSS feed names; ``failed_scrapers`` holds scraper
    labels such as ``Hacker News`` or ``GitHub``. A group with at least one
    source that is not in either set is merely empty, not failed.
    """
    failed_feeds = set(failed_feeds)
    failed_scrapers = set(failed_scrapers)
    result: dict[str, bool] = {}
    for group_id, sources in _sources_by_group(config).items():
        if not sources:
            continue
        all_failed = all(
            (label in failed_feeds) if kind == "feed" else (label in failed_scrapers)
            for kind, label in sources
        )
        if all_failed:
            result[group_id] = True
    return result


def write_payload(payload: SitePayload, web_dir: Path) -> tuple[Path, Path]:
    """Write the latest payload and its dated archive copy."""
    web_dir = Path(web_dir)
    archive_dir = web_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    text = json.dumps(payload.to_dict(), ensure_ascii=False, indent=2)
    latest = web_dir / "data.json"
    archive = archive_dir / f"{payload.date}.json"
    latest.write_text(text, encoding="utf-8")
    archive.write_text(text, encoding="utf-8")
    return latest, archive

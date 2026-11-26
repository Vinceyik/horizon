"""Serialisable payload for the personal briefing site."""

from dataclasses import dataclass, field
from typing import Literal, Optional

GroupStatus = Literal["ok", "empty", "failed"]


@dataclass(frozen=True)
class SiteItem:
    """One briefing entry, in the shape the front-end reads."""

    title: str
    original_title: str
    url: str
    source: str
    score: Optional[float]
    blurb: str
    summary: str
    data_points: list[str] = field(default_factory=list)
    published_at: str = ""

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "originalTitle": self.original_title,
            "url": self.url,
            "source": self.source,
            "score": self.score,
            "blurb": self.blurb,
            "summary": self.summary,
            "dataPoints": list(self.data_points),
            "publishedAt": self.published_at,
        }


@dataclass(frozen=True)
class SiteGroup:
    """One tab: a category with its items and executive summary."""

    id: str
    name: str
    overview: str
    status: GroupStatus
    note: Optional[str]
    items: list[SiteItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "overview": self.overview,
            "status": self.status,
            "note": self.note,
            "items": [item.to_dict() for item in self.items],
        }


@dataclass(frozen=True)
class SitePayload:
    """Everything one daily run publishes."""

    generated_at: str
    date: str
    language: str
    total_fetched: int
    selected: int
    groups: list[SiteGroup]
    failures: list[dict] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "generatedAt": self.generated_at,
            "date": self.date,
            "language": self.language,
            "totalFetched": self.total_fetched,
            "selected": self.selected,
            "groups": [group.to_dict() for group in self.groups],
            "failures": list(self.failures),
            "sources": list(self.sources),
        }

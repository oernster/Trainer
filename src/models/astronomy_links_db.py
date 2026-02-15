"""Astronomy links domain model + query API."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List
from urllib.parse import urlparse

from ..utils.url_utils import canonicalize_url

logger = logging.getLogger(__name__)


class LinkCategory(Enum):
    """Categories for astronomy links."""

    OBSERVATORY = "observatory"
    SPACE_AGENCY = "space_agency"
    ASTRONOMY_TOOL = "astronomy_tool"
    EDUCATIONAL = "educational"
    LIVE_DATA = "live_data"
    COMMUNITY = "community"
    TONIGHT_SKY = "tonight_sky"
    MOON_INFO = "moon_info"


@dataclass(frozen=True)
class AstronomyLink:
    """Immutable astronomy link data."""

    name: str
    url: str
    category: LinkCategory
    emoji: str
    description: str
    priority: int = 1  # 1=high, 2=medium, 3=low
    tags: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Link name cannot be empty")
        if not self.url.strip():
            raise ValueError("Link URL cannot be empty")
        if not self._is_valid_url(self.url):
            raise ValueError(f"Invalid URL: {self.url}")
        if not self.description.strip():
            raise ValueError("Link description cannot be empty")
        if not (1 <= self.priority <= 3):
            raise ValueError("Priority must be between 1 and 3")

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        try:
            result = urlparse(url)
            return bool(result.scheme and result.netloc)
        except Exception:
            return False


class AstronomyLinksDatabase:
    """Database of curated astronomy links with fast lookup and simple queries."""

    def __init__(self, links: Iterable[AstronomyLink]):
        self._links_by_key: Dict[str, AstronomyLink] = {}
        self._canon_to_key: Dict[str, str] = {}

        for link in links:
            self._add_link(link)

        logger.info("Initialized astronomy links database with %d links", len(self._links_by_key))

    @classmethod
    def from_links(cls, links: Iterable[AstronomyLink]) -> "AstronomyLinksDatabase":
        return cls(links)

    def _add_link(self, link: AstronomyLink) -> None:
        key = link.name.strip().lower()
        canon = canonicalize_url(link.url)

        # If URL duplicates an existing entry, keep the higher priority (lower number).
        if canon in self._canon_to_key:
            existing_key = self._canon_to_key[canon]
            existing = self._links_by_key[existing_key]
            if link.priority < existing.priority:
                self._links_by_key[existing_key] = link
            return

        self._links_by_key[key] = link
        self._canon_to_key[canon] = key

    def get_all_links(self) -> List[AstronomyLink]:
        return list(self._links_by_key.values())

    def get_links_by_category(self, category: LinkCategory) -> List[AstronomyLink]:
        return [l for l in self._links_by_key.values() if l.category == category]

    def get_links_by_priority(self, priority: int) -> List[AstronomyLink]:
        return [l for l in self._links_by_key.values() if l.priority == priority]

    def get_high_priority_links(self) -> List[AstronomyLink]:
        return self.get_links_by_priority(1)

    def search_links(self, query: str) -> List[AstronomyLink]:
        q = query.strip().lower()
        if not q:
            return []
        results: list[AstronomyLink] = []
        for link in self._links_by_key.values():
            haystack = " ".join([link.name, link.description, *link.tags]).lower()
            if q in haystack:
                results.append(link)
        return results

    def get_category_emoji(self, category: LinkCategory) -> str:
        mapping = {
            LinkCategory.OBSERVATORY: "🔭",
            LinkCategory.SPACE_AGENCY: "🚀",
            LinkCategory.ASTRONOMY_TOOL: "📱",
            LinkCategory.EDUCATIONAL: "📚",
            LinkCategory.LIVE_DATA: "📡",
            LinkCategory.COMMUNITY: "💬",
            LinkCategory.TONIGHT_SKY: "🌙",
            LinkCategory.MOON_INFO: "🌕",
        }
        return mapping.get(category, "🔗")

    def get_suggested_links_for_event_type(self, event_type: str) -> List[AstronomyLink]:
        # Lightweight heuristic mapping for now.
        event_type = (event_type or "").strip().lower()
        if event_type in {"apod", "satellite_image"}:
            categories = {LinkCategory.SPACE_AGENCY, LinkCategory.OBSERVATORY}
        elif event_type in {"iss_pass", "near_earth_object"}:
            categories = {LinkCategory.LIVE_DATA, LinkCategory.ASTRONOMY_TOOL}
        elif event_type in {"moon_phase"}:
            categories = {LinkCategory.MOON_INFO, LinkCategory.TONIGHT_SKY}
        else:
            categories = {LinkCategory.EDUCATIONAL, LinkCategory.ASTRONOMY_TOOL}

        links: list[AstronomyLink] = []
        for cat in categories:
            links.extend(self.get_links_by_category(cat))

        # Stable ordering: priority then name.
        return sorted(links, key=lambda l: (l.priority, l.name.lower()))


__all__ = ["LinkCategory", "AstronomyLink", "AstronomyLinksDatabase"]


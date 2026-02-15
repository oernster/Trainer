"""Astronomy links public API.

This module re-exports the domain model and provides a global
[`astronomy_links_db`](src/models/astronomy_links.py:1) instance.

The curated dataset is kept in
[`src/models/astronomy_links_data.py`](src/models/astronomy_links_data.py:1) to
keep each module below the <= 400 LOC gate.
"""

from __future__ import annotations

from .astronomy_links_db import AstronomyLink, AstronomyLinksDatabase, LinkCategory
from .astronomy_links_data import DEFAULT_ASTRONOMY_LINKS


astronomy_links_db = AstronomyLinksDatabase.from_links(DEFAULT_ASTRONOMY_LINKS)

__all__ = [
    "AstronomyLink",
    "AstronomyLinksDatabase",
    "LinkCategory",
    "astronomy_links_db",
]


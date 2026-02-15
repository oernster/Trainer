"""Curated astronomy links dataset.

Kept separate from the query / domain logic to satisfy the <=400 LOC gate.
"""

from __future__ import annotations

from .astronomy_links_db import AstronomyLink, LinkCategory


DEFAULT_ASTRONOMY_LINKS = [
    AstronomyLink(
        name="NASA",
        url="https://www.nasa.gov/",
        category=LinkCategory.SPACE_AGENCY,
        emoji="🚀",
        description="National Aeronautics and Space Administration",
        priority=1,
        tags=["nasa", "missions", "space"],
    ),
    AstronomyLink(
        name="European Space Agency",
        url="https://www.esa.int/",
        category=LinkCategory.SPACE_AGENCY,
        emoji="🚀",
        description="European space missions and research",
        priority=1,
        tags=["esa", "europe", "missions"],
    ),
    AstronomyLink(
        name="Hubble Space Telescope",
        url="https://hubblesite.org/",
        category=LinkCategory.OBSERVATORY,
        emoji="🔭",
        description="Latest images and discoveries from Hubble",
        priority=1,
        tags=["hubble", "telescope", "images"],
    ),
    AstronomyLink(
        name="James Webb Space Telescope",
        url="https://webb.nasa.gov/",
        category=LinkCategory.OBSERVATORY,
        emoji="🔭",
        description="Infrared astronomy from JWST",
        priority=1,
        tags=["jwst", "telescope", "infrared"],
    ),
    AstronomyLink(
        name="Stellarium",
        url="https://stellarium.org/",
        category=LinkCategory.ASTRONOMY_TOOL,
        emoji="📱",
        description="Free open-source planetarium software",
        priority=1,
        tags=["planetarium", "desktop", "free"],
    ),
    AstronomyLink(
        name="Heavens-Above",
        url="https://www.heavens-above.com/",
        category=LinkCategory.ASTRONOMY_TOOL,
        emoji="📱",
        description="Satellite tracking and predictions",
        priority=1,
        tags=["iss", "satellite", "tracking"],
    ),
    AstronomyLink(
        name="Time and Date: Astronomy",
        url="https://www.timeanddate.com/astronomy/",
        category=LinkCategory.EDUCATIONAL,
        emoji="📚",
        description="Astronomical calendars and calculations",
        priority=2,
        tags=["calendar", "sunrise", "sunset"],
    ),
]


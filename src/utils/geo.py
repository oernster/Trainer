"""Geospatial helpers.

This module intentionally stays dependency-free so it can be reused by services and UI.
"""

from __future__ import annotations

import math


def haversine_distance_km(coord1: dict, coord2: dict) -> float:
    """Return the Haversine distance in kilometers between two coordinates.

    The codebase stores coordinates as dicts with ``lat`` and ``lng`` keys.
    """

    lat1 = math.radians(coord1["lat"])
    lon1 = math.radians(coord1["lng"])
    lat2 = math.radians(coord2["lat"])
    lon2 = math.radians(coord2["lng"])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    earth_radius_km = 6371.0
    return earth_radius_km * c


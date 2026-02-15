"""Geospatial helpers for station database operations."""

from __future__ import annotations

from ...utils.geo import haversine_distance_km


def calculate_haversine_distance(coord1: dict, coord2: dict) -> float:
    """Calculate the distance in km between coordinates stored as {lat, lng}."""

    return haversine_distance_km(coord1, coord2)


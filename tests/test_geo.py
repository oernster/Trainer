from __future__ import annotations

import math

from src.utils.geo import haversine_distance_km


def test_haversine_distance_km_zero_distance_is_zero():
    coord = {"lat": 51.5, "lng": -0.12}
    assert haversine_distance_km(coord, coord) == 0.0


def test_haversine_distance_km_known_distance_equator_one_degree_longitude():
    # Along the equator, 1 degree of longitude is ~111.195km.
    coord1 = {"lat": 0.0, "lng": 0.0}
    coord2 = {"lat": 0.0, "lng": 1.0}
    dist = haversine_distance_km(coord1, coord2)
    assert math.isclose(dist, 111.195, rel_tol=0.0, abs_tol=0.5)


"""Walking penalty logic for pathfinding."""

from __future__ import annotations

from .interchange_connections import load_interchange_connections
from ....utils.geo import haversine_distance_km


def apply_walking_penalties(
    *,
    weight: float,
    connection: dict,
    current_station: str,
    avoid_walking: bool,
    max_walking_distance_km: float,
    data_repository,
    logger,
) -> float:
    """Apply penalties for walking connections based on preferences."""

    is_walking = False

    from_station = current_station
    to_station = connection["to_station"]

    interchange_connections = load_interchange_connections(logger=logger)
    for ic in interchange_connections.get("connections", []):
        if (
            (ic.get("from_station") == from_station and ic.get("to_station") == to_station)
            or (
                ic.get("from_station") == to_station
                and ic.get("to_station") == from_station
            )
        ):
            if ic.get("connection_type") == "WALKING":
                is_walking = True
                logger.debug(
                    "Walking connection detected: %s -> %s (from interchange_connections.json)",
                    from_station,
                    to_station,
                )
                break

    if not is_walking:
        from_coords = None
        to_coords = None

        for ic in interchange_connections.get("connections", []):
            if (
                (ic.get("from_station") == from_station and ic.get("to_station") == to_station)
                or (
                    ic.get("from_station") == to_station
                    and ic.get("to_station") == from_station
                )
            ):
                coords = ic.get("coordinates", {})
                if coords:
                    if ic.get("from_station") == from_station:
                        from_coords = coords.get("from")
                        to_coords = coords.get("to")
                    else:
                        from_coords = coords.get("to")
                        to_coords = coords.get("from")
                    break

        if from_coords and to_coords:
            distance_km = haversine_distance_km(from_coords, to_coords)
            logger.debug(
                "Haversine distance: %s -> %s = %.3fkm",
                from_station,
                to_station,
                distance_km,
            )
            if distance_km > max_walking_distance_km:
                is_walking = True
                logger.debug(
                    "Walking connection by distance: %s -> %s (%.3fkm > %.3fkm)",
                    from_station,
                    to_station,
                    distance_km,
                    max_walking_distance_km,
                )
        else:
            same_line = False
            clean_from = from_station.replace(" (Main)", "").replace(
                " (Cross Country Line)", ""
            )
            clean_to = to_station.replace(" (Main)", "").replace(
                " (Cross Country Line)", ""
            )
            for line in data_repository.load_railway_lines():
                line_stations = [
                    s.replace(" (Main)", "").replace(" (Cross Country Line)", "")
                    for s in line.stations
                ]
                if clean_from in line_stations and clean_to in line_stations:
                    same_line = True
                    break

            distance_km = connection.get("distance", 0)
            if not same_line and distance_km > max_walking_distance_km:
                is_walking = True
                logger.debug(
                    "Walking connection by fallback: %s -> %s (not same line, distance: %.3fkm)",
                    from_station,
                    to_station,
                    distance_km,
                )

    if is_walking or connection.get("line") == "WALKING" or connection.get(
        "is_walking_connection", False
    ):
        if avoid_walking:
            logger.debug(
                "Avoid walking: Skipping walking connection: %s -> %s",
                current_station,
                to_station,
            )
            return float("inf")

        connection["is_walking_connection"] = True
        connection["line"] = "WALKING"

        penalty_multiplier = connection.get("walking_penalty", 2)
        original_weight = weight
        weight = weight * penalty_multiplier
        logger.debug(
            "Walking connection allowed: %s -> %s (penalty applied: %.1f -> %.1f)",
            current_station,
            to_station,
            original_weight,
            weight,
        )

    return weight


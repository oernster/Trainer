"""Underground routing bonus logic for pathfinding."""

from __future__ import annotations

from .types import PathNode


def apply_underground_routing_bonus(
    *,
    weight: float,
    connection: dict,
    current: PathNode,
    start: str,
    end: str,
    logger,
) -> float:
    """Apply bonus for Underground routing when it's beneficial for cross-London journeys."""

    if connection.get("line") != "London Underground":
        return weight

    from_is_london = "London" in start
    to_is_london = "London" in end
    journey_distance = current.distance
    to_station = connection.get("to_station", "")

    is_cross_country_route = False
    if ("Southampton" in start and "Glasgow" in end) or (
        "Glasgow" in start and "Southampton" in end
    ):
        is_cross_country_route = True
        logger.info(
            "Detected cross-country route that should use London Underground: %s → %s",
            start,
            end,
        )

    major_terminals = [
        "London Waterloo",
        "London Liverpool Street",
        "London Victoria",
        "London Paddington",
        "London Kings Cross",
        "London St Pancras",
        "London Euston",
        "London Bridge",
    ]

    connects_to_major_terminal = to_station in major_terminals

    bonus_factor = 1.0
    original_weight = weight

    is_cross_london_journey = (
        (not from_is_london)
        and (not to_is_london)
        and (journey_distance > 20 or is_cross_country_route)
    )

    if connects_to_major_terminal:
        if is_cross_london_journey:
            bonus_factor = 0.3
            logger.info(
                "Major Underground bonus (cross-London via terminal): %s -> %s",
                current.station,
                to_station,
            )

            if is_cross_country_route:
                bonus_factor = 0.2
                logger.info(
                    "Extra Underground bonus for cross-country route: %s → %s",
                    start,
                    end,
                )
        elif journey_distance > 15:
            bonus_factor = 0.6
            logger.info(
                "Medium Underground bonus (to terminal): %s -> %s",
                current.station,
                to_station,
            )
        else:
            bonus_factor = 0.8
            logger.info(
                "Small Underground bonus (short to terminal): %s -> %s",
                current.station,
                to_station,
            )
    elif is_cross_london_journey:
        bonus_factor = 0.7
        logger.info(
            "Standard Underground bonus (cross-London): %s -> %s",
            current.station,
            to_station,
        )

    if bonus_factor < 1.0:
        weight = weight * bonus_factor
        logger.info(
            "Underground routing bonus applied: %s -> %s (weight: %.1f -> %.1f, factor: %.1f)",
            current.station,
            to_station,
            original_weight,
            weight,
            bonus_factor,
        )

    return weight


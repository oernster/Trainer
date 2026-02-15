"""Fallback routing helpers extracted from StationDatabaseManager."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def find_simple_direct_route(*, manager, from_name: str, to_name: str):
    """Find a simple direct route between two stations on the same line."""

    try:
        from_lines = set(manager.get_railway_lines_for_station(from_name))
        to_lines = set(manager.get_railway_lines_for_station(to_name))
        common_lines = from_lines.intersection(to_lines)

        if common_lines:
            line_name = list(common_lines)[0]
            return manager._find_direct_route_on_line(from_name, to_name, line_name)

        return None

    except Exception as exc:  # pragma: no cover
        logger.warning("Error in simple direct route: %s", exc)
        return None


def find_simple_routes(*, manager, from_name: str, to_name: str, max_changes: int = 3):
    """Simple fallback routing without service patterns."""

    try:
        routes = []

        direct_route = manager._find_simple_direct_route(from_name, to_name)
        if direct_route:
            routes.append(direct_route)
            return routes

        major_interchanges = [
            "London Waterloo",
            "Victoria",
            "London Bridge",
            "Paddington",
            "King's Cross",
            "Euston",
            "Liverpool Street",
            "Clapham Junction",
            "Birmingham New Street",
            "Manchester Piccadilly",
        ]

        from_lines = set(manager.get_railway_lines_for_station(from_name))
        to_lines = set(manager.get_railway_lines_for_station(to_name))

        for interchange_name in major_interchanges:
            if interchange_name == from_name or interchange_name == to_name:
                continue

            interchange_lines = set(manager.get_railway_lines_for_station(interchange_name))

            if (
                from_lines.intersection(interchange_lines)
                and to_lines.intersection(interchange_lines)
            ):
                first_leg = manager._find_simple_direct_route(from_name, interchange_name)
                second_leg = manager._find_simple_direct_route(interchange_name, to_name)

                if first_leg and second_leg:
                    combined_route = first_leg + second_leg[1:]
                    routes.append(combined_route)

                    if len(routes) >= 3:
                        break

        return routes

    except Exception as exc:  # pragma: no cover
        logger.error("Error in simple routing: %s", exc)
        return []


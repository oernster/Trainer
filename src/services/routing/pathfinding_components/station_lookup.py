"""Station lookup helpers for the network graph."""

from __future__ import annotations

from typing import Optional


def find_station_in_graph(*, station_name: str, graph: dict, logger) -> Optional[str]:
    """Find a station in ``graph`` and return the actual key if found.

    Handles case-insensitivity and common "London " prefix variants.
    """

    if station_name in graph:
        return station_name

    for graph_station in graph:
        if graph_station.lower() == station_name.lower():
            logger.info("Graph lookup (case): '%s' → '%s'", station_name, graph_station)
            return graph_station

    station_lower = station_name.lower()
    if station_lower.startswith("london "):
        base_name = station_lower[7:]
        for graph_station in graph:
            if graph_station.lower() == base_name:
                logger.info(
                    "Graph lookup (removed London): '%s' → '%s'",
                    station_name,
                    graph_station,
                )
                return graph_station
    else:
        london_name = "london " + station_lower
        for graph_station in graph:
            if graph_station.lower() == london_name:
                logger.info(
                    "Graph lookup (added London): '%s' → '%s'", station_name, graph_station
                )
                return graph_station

    return None


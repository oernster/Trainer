"""Connection selection logic for pathfinding."""

from __future__ import annotations

from typing import Optional

from .types import PathNode


def get_best_connection(
    *,
    connections: list[dict],
    current: PathNode,
    start: str,
    end: str,
    weight_func: str,
    data_repository,
    logger,
) -> Optional[dict]:
    """Return the best connection based on the chosen weight function and priorities."""

    if not connections:
        return None

    def get_connection_priority(conn: dict) -> float:
        """Calculate connection priority - lower is better."""

        base_weight = conn["time"] if weight_func == "time" else conn.get("distance", conn["time"])

        # Special case for Farnborough routes.
        if "Farnborough" in start:
            if conn["line"] == "South Western Main Line" and "Waterloo" in conn.get(
                "to_station", ""
            ):
                logger.debug("Priority: South Western Main Line to Waterloo")
                return base_weight - 100000

        # Walking connection between Farnborough North and Farnborough (Main).
        if (
            "Farnborough North" in current.station
            and "Farnborough (Main)" in conn["to_station"]
        ) or (
            "Farnborough (Main)" in current.station
            and "Farnborough North" in conn["to_station"]
        ):
            logger.debug("Prioritizing Farnborough walking connection")
            return base_weight - 10000

        # Check if both start and end stations are on the same line.
        start_lines: set[str] = set()
        end_lines: set[str] = set()

        for line in data_repository.load_railway_lines():
            if start in line.stations:
                start_lines.add(line.name)
            if end in line.stations:
                end_lines.add(line.name)

        common_lines = start_lines.intersection(end_lines)

        # If this connection uses a line that serves both start and end stations,
        # give it massive priority to prevent line switching.
        if conn["line"] in common_lines:
            return base_weight - 10000

        # Strong preference for staying on the same line as the current path.
        if current.lines_used:
            current_line = current.lines_used[-1]
            if conn["line"] == current_line:
                return base_weight - 1000

        # Secondary preference for direct connections.
        if conn.get("is_direct", False):
            return base_weight - 100

        return float(base_weight)

    if weight_func == "changes":

        def changes_priority(conn: dict) -> tuple[int, int]:
            start_lines: set[str] = set()
            end_lines: set[str] = set()

            for line in data_repository.load_railway_lines():
                if start in line.stations:
                    start_lines.add(line.name)
                if end in line.stations:
                    end_lines.add(line.name)

            common_lines = start_lines.intersection(end_lines)

            if conn["line"] in common_lines:
                return (0, conn["time"] - 20000)

            if current.lines_used and conn["line"] == current.lines_used[-1]:
                return (0, conn["time"] - 2000)
            if conn.get("is_direct", False):
                return (0, conn["time"] - 1000)
            return (1, conn["time"])

        return min(connections, key=changes_priority)

    return min(connections, key=get_connection_priority)


"""Weight calculation for pathfinding."""

from __future__ import annotations


def calculate_weight(
    *,
    weight_func: str,
    new_time: int,
    new_distance: float,
    new_changes: int,
    best_connection: dict,
) -> float:
    """Calculate the Dijkstra priority weight according to the chosen strategy."""

    if weight_func == "time":
        return float(new_time)
    if weight_func == "distance":
        return float(new_distance)
    if weight_func == "changes":
        # Heavily penalize changes, but give direct connections a big advantage.
        direct_bonus = 0 if best_connection.get("is_direct", False) else 1000
        return float((new_changes * 1000) + direct_bonus + new_time)

    return float(new_time)


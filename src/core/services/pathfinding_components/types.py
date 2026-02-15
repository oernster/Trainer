"""Types used by pathfinding services."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PathNode:
    """Node for pathfinding algorithms."""

    station: str
    distance: float
    time: int
    changes: int
    path: list[str]
    lines_used: list[str]

    def __lt__(self, other: "PathNode") -> bool:
        # For priority queue - prioritize by time, then changes, then distance.
        if self.time != other.time:
            return self.time < other.time
        if self.changes != other.changes:
            return self.changes < other.changes
        return self.distance < other.distance


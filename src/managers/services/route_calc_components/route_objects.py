"""Route/segment construction helpers for `RouteCalculationService`."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class MinimalSegment:
    from_station: str
    to_station: str
    is_walking: bool = False
    distance_km: float = 10.0
    time_minutes: int = 15
    train_service_id: Optional[str] = None

    @property
    def line_name(self) -> str:
        return "WALKING" if self.is_walking else "National Rail"

    @property
    def journey_time_minutes(self) -> int:
        return self.time_minutes


@dataclass
class MinimalRoute:
    full_path: list[str]
    avoid_walking: bool = False
    walking_connections: Optional[dict] = None

    def __post_init__(self) -> None:
        self.from_station = self.full_path[0]
        self.to_station = self.full_path[-1]
        self.total_journey_time_minutes = len(self.full_path) * 10
        self.total_distance_km = len(self.full_path) * 15
        self.changes_required = max(0, len(self.full_path) - 2)
        self.segments: list[MinimalSegment] = []
        self._is_valid = True

        wc = self.walking_connections or {}
        for i in range(len(self.full_path) - 1):
            from_stn = self.full_path[i]
            to_stn = self.full_path[i + 1]
            station_pair = (from_stn, to_stn)
            is_walking = station_pair in wc

            if self.avoid_walking and is_walking:
                self._is_valid = False

            distance_km = 10.0
            time_minutes = 15
            if is_walking:
                conn_info = wc.get(station_pair, {})
                distance_km = conn_info.get("distance_km", distance_km)
                time_minutes = conn_info.get("time_minutes", time_minutes)

            line_name = "WALKING" if is_walking else "National Rail"
            train_service_id = f"MINIMAL_{line_name}_{from_stn}_{to_stn}"

            self.segments.append(
                MinimalSegment(
                    from_station=from_stn,
                    to_station=to_stn,
                    is_walking=is_walking,
                    distance_km=distance_km,
                    time_minutes=time_minutes,
                    train_service_id=train_service_id,
                )
            )
            self.total_journey_time_minutes += time_minutes - 10
            self.total_distance_km += distance_km - 15

    @property
    def intermediate_stations(self) -> list[str]:
        return self.full_path[1:-1] if len(self.full_path) > 2 else []

    @property
    def is_valid(self) -> bool:
        return bool(self._is_valid)


@dataclass
class RouteSegment:
    from_station: str
    to_station: str
    line_name: str
    station_count: int = 1
    service_pattern: Optional[str] = None
    train_service_id: Optional[str] = None

    @property
    def distance_km(self) -> float:
        return 15 * self.station_count

    @property
    def journey_time_minutes(self) -> int:
        return 10 * self.station_count


def create_route_segments_from_path(
    *,
    service,
    path: list[str],
    line_data: dict[str, dict],
) -> list[RouteSegment]:
    """Create route segments with line change information from a station path."""

    if not path or len(path) < 2:
        return []

    station_to_lines = service._build_station_to_lines_mapping(line_data)

    segments: list[RouteSegment] = []
    segment_start = 0
    current_line: str | None = None

    for i, station in enumerate(path):
        station_lines = set(station_to_lines.get(station, []))

        if i == 0:
            current_line = list(station_lines)[0] if station_lines else "Unknown Line"
            continue

        if current_line in station_lines:
            continue

        segment_end = i - 1
        if segment_end > segment_start:
            from_station = path[segment_start]
            to_station = path[segment_end]
            station_count = segment_end - segment_start
            service_pattern = "WALKING" if current_line == "WALKING" else None
            train_service_id = service._generate_train_service_id(
                current_line or "Unknown Line",
                service_pattern,
                from_station,
                to_station,
            )
            segments.append(
                RouteSegment(
                    from_station=from_station,
                    to_station=to_station,
                    line_name=current_line or "Unknown Line",
                    station_count=station_count,
                    service_pattern=service_pattern,
                    train_service_id=train_service_id,
                )
            )

        segment_start = i - 1
        prev_station = path[i - 1]
        prev_lines = set(station_to_lines.get(prev_station, []))
        common_lines = prev_lines & station_lines
        if common_lines:
            current_line = list(common_lines)[0]
        elif station_lines:
            current_line = list(station_lines)[0]
        else:
            current_line = "Unknown Line"

    if segment_start < len(path) - 1:
        from_station = path[segment_start]
        to_station = path[-1]
        station_count = len(path) - 1 - segment_start
        service_pattern = "WALKING" if current_line == "WALKING" else None
        train_service_id = service._generate_train_service_id(
            current_line or "Unknown Line",
            service_pattern,
            from_station,
            to_station,
        )
        segments.append(
            RouteSegment(
                from_station=from_station,
                to_station=to_station,
                line_name=current_line or "Unknown Line",
                station_count=station_count,
                service_pattern=service_pattern,
                train_service_id=train_service_id,
            )
        )

    logger.debug("Created %s route segments", len(segments))
    return segments


def create_minimal_route(
    *,
    path: list[str],
    avoid_walking: bool = False,
    walking_connections: Optional[dict] = None,
) -> Any:
    """Create a minimal route-like object with essential properties."""

    return MinimalRoute(
        full_path=path,
        avoid_walking=avoid_walking,
        walking_connections=walking_connections,
    )


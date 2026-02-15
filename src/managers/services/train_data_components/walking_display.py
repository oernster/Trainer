"""Walking-connection display helpers for `TrainDataService`."""

from __future__ import annotations

import logging
from datetime import timedelta

from ....models.train_data import CallingPoint

logger = logging.getLogger(__name__)


def process_walking_connection_display(
    *,
    service,
    station_name: str,
    segments,
    calling_points: list[CallingPoint],
    station_time,
) -> str:
    """Insert walking text calling points when a walking connection is encountered."""

    avoid_walking = False
    if service.config and hasattr(service.config, "avoid_walking"):
        avoid_walking = bool(service.config.avoid_walking)

    is_walking = False
    walking_distance = None
    walking_time = None

    for segment in segments:
        if getattr(segment, "line_name", None) == "WALKING":
            if (
                getattr(segment, "from_station", None) == station_name
                or getattr(segment, "to_station", None) == station_name
            ):
                is_walking = True
                walking_distance = getattr(segment, "distance_km", None)
                walking_time = getattr(segment, "journey_time_minutes", None)
                if not walking_time and walking_distance:
                    walking_time = int(walking_distance / 0.107)
                break

    if not is_walking:
        for segment in segments:
            if getattr(segment, "service_pattern", None) == "WALKING":
                if (
                    getattr(segment, "from_station", None) == station_name
                    or getattr(segment, "to_station", None) == station_name
                ):
                    is_walking = True
                    walking_distance = getattr(segment, "distance_km", None)
                    walking_time = getattr(segment, "journey_time_minutes", None)
                    if not walking_time and walking_distance:
                        walking_time = int(walking_distance / 0.107)
                    break

    if is_walking and not avoid_walking:
        prev_station = calling_points[-1].station_name if calling_points else None

        if walking_distance and walking_time:
            walking_text = (
                f"<font color='#f44336'>Walk {walking_distance:.1f}km ({walking_time}min)</font>"
            )
        elif walking_distance:
            walking_text = f"<font color='#f44336'>Walk {walking_distance:.1f}km</font>"
        else:
            walking_text = "<font color='#f44336'>Walking connection</font>"

        if prev_station:
            walk_time = station_time - timedelta(minutes=int(walking_time or 10))
            calling_points.append(
                CallingPoint(
                    station_name=walking_text,
                    scheduled_arrival=walk_time,
                    scheduled_departure=walk_time,
                    expected_arrival=walk_time,
                    expected_departure=walk_time,
                    platform=None,
                    is_origin=False,
                    is_destination=False,
                )
            )
            logger.info("Added walking text between %s and %s", prev_station, station_name)

    elif is_walking and avoid_walking:
        logger.info(
            "Skipping walking connection display for %s due to avoid_walking preference",
            station_name,
        )

    return station_name


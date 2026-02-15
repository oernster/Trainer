"""Intermediate station extraction helpers for `TrainDataService`."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def extract_intermediate_stations(*, service, route_result, from_station: str, to_station: str):
    """Extract intermediate stations from route result, respecting Underground black box segments."""

    intermediate_stations: list[str] = []
    underground_segments_processed: list[str] = []
    underground_systems_added: set[str] = set()

    if hasattr(route_result, "segments") and route_result.segments:
        for segment in route_result.segments:
            if not all(
                hasattr(segment, attr)
                for attr in ["service_pattern", "from_station", "to_station"]
            ):
                continue

            if getattr(segment, "service_pattern", "") == "UNDERGROUND":
                logger.debug(
                    "Underground black box segment: %s -> %s (using black box display)",
                    segment.from_station,
                    segment.to_station,
                )

                segment_id = (
                    f"{segment.from_station}->{segment.to_station}-"
                    f"{getattr(segment, 'line_name', 'Underground')}"
                )
                system_name = getattr(segment, "line_name", "Underground")

                if segment_id not in underground_segments_processed:
                    underground_segments_processed.append(segment_id)

                    from_station_name = segment.from_station
                    if (
                        from_station_name != from_station
                        and from_station_name != to_station
                        and from_station_name not in intermediate_stations
                    ):
                        intermediate_stations.append(from_station_name)

                    if system_name not in underground_systems_added:
                        underground_indicator = service._get_underground_indicator_for_segment(
                            segment
                        )
                        if underground_indicator not in intermediate_stations:
                            intermediate_stations.append(underground_indicator)
                            underground_systems_added.add(system_name)
                            logger.debug("Added underground indicator for %s", system_name)
                    else:
                        logger.debug(
                            "Skipping duplicate underground indicator for %s",
                            system_name,
                        )

                    to_station_name = segment.to_station
                    if (
                        to_station_name != from_station
                        and to_station_name != to_station
                        and to_station_name not in intermediate_stations
                    ):
                        intermediate_stations.append(to_station_name)

                continue

            from_station_name = segment.from_station
            to_station_name = segment.to_station

            if (
                from_station_name != from_station
                and from_station_name != to_station
                and from_station_name not in intermediate_stations
            ):
                intermediate_stations.append(from_station_name)

            if (
                to_station_name != from_station
                and to_station_name != to_station
                and to_station_name not in intermediate_stations
            ):
                intermediate_stations.append(to_station_name)

        logger.debug(
            "Extracted %s intermediate stations from segments (National Rail + Underground endpoints)",
            len(intermediate_stations),
        )
        logger.debug("Underground systems processed: %s", underground_systems_added)

    elif hasattr(route_result, "full_path") and route_result.full_path:
        full_path = route_result.full_path
        if len(full_path) > 2:
            for station in full_path[1:-1]:
                if service._should_show_station_in_calling_points(station):
                    intermediate_stations.append(station)
            logger.debug(
                "Using filtered full_path with %s intermediate stations",
                len(intermediate_stations),
            )

    if len(intermediate_stations) <= 1 and hasattr(route_result, "full_path") and route_result.full_path:
        logger.debug("Segments didn't provide enough detail, using full_path as primary source")
        intermediate_stations = []
        full_path = route_result.full_path
        if len(full_path) > 2:
            for station in full_path[1:-1]:
                if service._should_show_station_in_calling_points(station):
                    intermediate_stations.append(station)
            logger.debug(
                "Using full_path as primary source with %s intermediate stations",
                len(intermediate_stations),
            )

    elif hasattr(route_result, "intermediate_stations") and route_result.intermediate_stations:
        for station in route_result.intermediate_stations:
            if service._should_show_station_in_calling_points(station):
                intermediate_stations.append(station)
        logger.debug(
            "Using filtered intermediate_stations property with %s stations",
            len(intermediate_stations),
        )

    return intermediate_stations


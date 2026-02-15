"""Interchange analysis helpers extracted from InterchangeDetectionService."""

from __future__ import annotations

from typing import Any


def detect_user_journey_interchanges(*, service, route_segments: list[Any]):
    """Detect actual user journey interchanges from route segments."""

    try:
        if not route_segments or len(route_segments) < 2:
            service.logger.debug(
                "No route segments or insufficient segments for interchange detection"
            )
            return []

        interchanges = []

        for i in range(len(route_segments) - 1):
            try:
                current_segment = route_segments[i]
                next_segment = route_segments[i + 1]

                if not all(
                    hasattr(current_segment, attr) for attr in ["to_station", "line_name"]
                ):
                    service.logger.warning(
                        "Current segment %s missing required attributes",
                        i,
                    )
                    continue

                if not all(
                    hasattr(next_segment, attr)
                    for attr in ["from_station", "line_name"]
                ):
                    service.logger.warning(
                        "Next segment %s missing required attributes",
                        i + 1,
                    )
                    continue

                connection_station = current_segment.to_station
                from_line = current_segment.line_name
                to_line = next_segment.line_name

                if not connection_station or not from_line or not to_line:
                    service.logger.warning(
                        "Empty station or line names in segments %s-%s",
                        i,
                        i + 1,
                    )
                    continue

                if from_line != to_line and connection_station == next_segment.from_station:
                    interchange = service._analyze_interchange(
                        connection_station,
                        from_line,
                        to_line,
                        current_segment,
                        next_segment,
                    )
                    if interchange:
                        interchanges.append(interchange)

            except Exception as exc:  # pragma: no cover
                service.logger.error("Error processing segment %s: %s", i, exc)
                continue

        service.logger.debug("Detected %s potential interchanges", len(interchanges))
        return interchanges

    except Exception as exc:  # pragma: no cover
        service.logger.error("Error in detect_user_journey_interchanges: %s", exc)
        return []


def analyze_interchange(
    *,
    service,
    station_name: str,
    from_line: str,
    to_line: str,
    current_segment: Any,
    next_segment: Any,
):
    """Analyze a potential interchange to determine if it's a real user journey change."""

    InterchangePoint = service.InterchangePoint
    InterchangeType = service.InterchangeType

    if service._is_known_through_service(from_line, to_line, station_name):
        service.logger.debug(
            "Through service detected at %s: %s -> %s",
            station_name,
            from_line,
            to_line,
        )
        return InterchangePoint(
            station_name=station_name,
            from_line=from_line,
            to_line=to_line,
            interchange_type=InterchangeType.THROUGH_SERVICE,
            walking_time_minutes=0,
            is_user_journey_change=False,
            description="Through service - same train continues",
        )

    if not service._is_meaningful_user_journey_change(
        from_line,
        to_line,
        station_name,
        current_segment,
        next_segment,
    ):
        service.logger.debug(
            "Not a meaningful user journey change at %s: %s -> %s",
            station_name,
            from_line,
            to_line,
        )
        return InterchangePoint(
            station_name=station_name,
            from_line=from_line,
            to_line=to_line,
            interchange_type=InterchangeType.THROUGH_SERVICE,
            walking_time_minutes=0,
            is_user_journey_change=False,
            description="Same train continues with different line designation",
        )

    if service._are_stations_on_same_line(from_line, to_line):
        service.logger.debug(
            "Stations are on the same line, no walking needed: %s -> %s",
            from_line,
            to_line,
        )
        return InterchangePoint(
            station_name=station_name,
            from_line=from_line,
            to_line=to_line,
            interchange_type=InterchangeType.THROUGH_SERVICE,
            walking_time_minutes=0,
            is_user_journey_change=False,
            description="Stations are on the same line, no change required",
        )

    if not service._is_valid_interchange_geographically(station_name, from_line, to_line):
        service.logger.debug(
            "Invalid geographic interchange at %s: %s -> %s",
            station_name,
            from_line,
            to_line,
        )
        return None

    walking_time = service._calculate_interchange_walking_time(
        station_name,
        from_line,
        to_line,
    )

    if walking_time > 10:
        interchange_type = InterchangeType.WALKING_CONNECTION
        is_journey_change = True
    else:
        interchange_type = InterchangeType.TRAIN_CHANGE
        is_journey_change = True

    service.logger.debug(
        "Valid interchange detected at %s: %s -> %s",
        station_name,
        from_line,
        to_line,
    )

    return InterchangePoint(
        station_name=station_name,
        from_line=from_line,
        to_line=to_line,
        interchange_type=interchange_type,
        walking_time_minutes=walking_time,
        is_user_journey_change=is_journey_change,
        coordinates=service._get_station_coordinates().get(station_name),
        description=f"Change from {from_line} to {to_line}",
    )


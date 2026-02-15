"""Journey-change classification helpers extracted from InterchangeDetectionService."""

from __future__ import annotations

from typing import Any


def is_known_through_service(*, service, line1: str, line2: str, station_name: str) -> bool:
    """Check if this represents a known through service using data-driven approach."""

    line_interchanges = service._get_line_interchanges()
    if station_name not in line_interchanges:
        return False

    connections = line_interchanges[station_name]

    for connection in connections:
        from_line = connection.get("from_line", "")
        to_line = connection.get("to_line", "")
        requires_change = connection.get("requires_change", True)

        if not requires_change and (
            (from_line == line1 and to_line == line2)
            or (from_line == line2 and to_line == line1)
        ):
            return True

    return False


def is_continuous_train_service(*, service, from_line: str, to_line: str, station_name: str) -> bool:
    """Check if the same train continues with a different line designation."""

    line_interchanges = service._get_line_interchanges()
    for _station, connections in line_interchanges.items():
        for connection in connections:
            connection_from_line = connection.get("from_line", "")
            connection_to_line = connection.get("to_line", "")
            requires_change = connection.get("requires_change", True)

            if not requires_change and (
                (connection_from_line == from_line and connection_to_line == to_line)
                or (connection_from_line == to_line and connection_to_line == from_line)
            ):
                return True

    return False


def is_through_station_for_journey(
    *,
    service,
    station_name: str,
    from_line: str,
    to_line: str,
    current_segment: Any,
    next_segment: Any,
) -> bool:
    """True if the user does not need to change trains at this station."""

    current_train_service_id = getattr(current_segment, "train_service_id", None)
    next_train_service_id = getattr(next_segment, "train_service_id", None)

    if current_train_service_id and next_train_service_id:
        if current_train_service_id == next_train_service_id:
            service.logger.debug("Same train service ID detected: %s", current_train_service_id)
            return True

        service.logger.debug(
            "Different train service IDs: %s != %s",
            current_train_service_id,
            next_train_service_id,
        )
        return False

    current_service = getattr(current_segment, "service_pattern", None)
    next_service = getattr(next_segment, "service_pattern", None)
    if current_service and next_service and current_service == next_service:
        service.logger.debug("Same service pattern detected: %s", current_service)
        return True

    current_train_id = getattr(current_segment, "train_id", None)
    next_train_id = getattr(next_segment, "train_id", None)
    if current_train_id and next_train_id and current_train_id == next_train_id:
        service.logger.debug("Same train ID detected: %s", current_train_id)
        return True

    return service._is_known_through_service(from_line, to_line, station_name)


def is_json_file_line_change(*, service, line1: str, line2: str) -> bool:
    """True if lines map to different JSON files."""

    line_to_file = service._get_line_to_json_file_mapping()
    file1 = line_to_file.get(line1)
    file2 = line_to_file.get(line2)

    if not file1 or not file2:
        return True

    return file1 != file2


def is_meaningful_user_journey_change(
    *,
    service,
    from_line: str,
    to_line: str,
    station_name: str,
    current_segment: Any,
    next_segment: Any,
) -> bool:
    """True if passenger must change trains (not just a line designation change)."""

    service.logger.debug("Analyzing %s: %s -> %s", station_name, from_line, to_line)

    is_json_change = service._is_json_file_line_change(from_line, to_line)
    service.logger.debug("%s JSON file change: %s", station_name, is_json_change)
    if not is_json_change:
        service.logger.debug(
            "Same network detected at %s: %s -> %s",
            station_name,
            from_line,
            to_line,
        )
        return False

    is_continuous = service._is_continuous_train_service(from_line, to_line, station_name)
    service.logger.debug("%s continuous service: %s", station_name, is_continuous)
    if is_continuous:
        service.logger.debug(
            "Continuous train service at %s: %s -> %s",
            station_name,
            from_line,
            to_line,
        )
        return False

    is_through = service._is_through_station_for_journey(
        station_name,
        from_line,
        to_line,
        current_segment,
        next_segment,
    )
    service.logger.debug("%s through station: %s", station_name, is_through)
    if is_through:
        service.logger.debug(
            "Through station for journey at %s: %s -> %s",
            station_name,
            from_line,
            to_line,
        )
        return False

    service.logger.debug(
        "%s marked as REAL INTERCHANGE requiring user action",
        station_name,
    )
    return True


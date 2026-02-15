"""Post-processing helpers for `TrainDataService`."""

from __future__ import annotations

import logging

from ....models.train_data import TrainData

logger = logging.getLogger(__name__)


def process_train_data(*, trains: list[TrainData]) -> list[TrainData]:
    """Filter/sort trains and apply essential calling-points reduction."""

    from ....utils.helpers import filter_trains_by_status, sort_trains_by_departure
    from ....services.routing.essential_stations_filter import EssentialStationsFilter

    filtered_trains = filter_trains_by_status(trains, include_cancelled=False)
    sorted_trains = sort_trains_by_departure(filtered_trains)

    processed_trains: list[TrainData] = []
    for train in sorted_trains:
        try:
            essential_calling_points = EssentialStationsFilter.filter_to_essential_stations(
                train.calling_points,
                train.route_segments,
            )

            processed_trains.append(
                TrainData(
                    departure_time=train.departure_time,
                    scheduled_departure=train.scheduled_departure,
                    destination=train.destination,
                    platform=train.platform,
                    operator=train.operator,
                    service_type=train.service_type,
                    status=train.status,
                    delay_minutes=train.delay_minutes,
                    estimated_arrival=train.estimated_arrival,
                    journey_duration=train.journey_duration,
                    current_location=train.current_location,
                    train_uid=train.train_uid,
                    service_id=train.service_id,
                    calling_points=essential_calling_points,  # Filtered for main display
                    route_segments=train.route_segments,
                    full_calling_points=train.calling_points,  # Complete route for route dialog
                )
            )

        except Exception as exc:  # pragma: no cover
            logger.warning("Error filtering stations for train %s: %s", train.service_id, exc)
            processed_trains.append(
                TrainData(
                    departure_time=train.departure_time,
                    scheduled_departure=train.scheduled_departure,
                    destination=train.destination,
                    platform=train.platform,
                    operator=train.operator,
                    service_type=train.service_type,
                    status=train.status,
                    delay_minutes=train.delay_minutes,
                    estimated_arrival=train.estimated_arrival,
                    journey_duration=train.journey_duration,
                    current_location=train.current_location,
                    train_uid=train.train_uid,
                    service_id=train.service_id,
                    calling_points=train.calling_points,
                    route_segments=train.route_segments,
                    full_calling_points=train.calling_points,
                )
            )

    max_trains_limit = max(100, 15)
    limited_trains = processed_trains[:max_trains_limit]

    if trains:
        original_stations = sum(
            len(train.calling_points) for train in trains[: len(limited_trains)]
        )
        filtered_stations = sum(len(train.calling_points) for train in limited_trains)
        reduction_percent = (
            int((1 - filtered_stations / original_stations) * 100)
            if original_stations > 0
            else 0
        )

        logger.info("Processed %s -> %s trains", len(trains), len(limited_trains))
        logger.info(
            "Reduced stations: %s -> %s (%s%% reduction)",
            original_stations,
            filtered_stations,
            reduction_percent,
        )

    return limited_trains


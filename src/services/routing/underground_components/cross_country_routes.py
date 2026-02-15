"""Cross-country (region-to-region) route construction.

Split out of `RouteFactory` (moved in Phase 2)
to keep the module under the <= 400 non-blank LOC gate.
"""

from __future__ import annotations

import logging
from typing import Optional

from src.core.models.route import Route, RouteSegment


def create_cross_country_route(factory, from_station: str, to_station: str) -> Optional[Route]:
    """Create a route for cross-country journeys that should go through London."""

    if not factory.geographic_utils.is_cross_country_route(from_station, to_station):
        return None

    logger = logging.getLogger(__name__)
    logger.info("Creating cross-country route: %s → %s", from_station, to_station)

    from_region = factory.geographic_utils._get_station_region(from_station)
    to_region = factory.geographic_utils._get_station_region(to_station)

    southern_terminals = factory.geographic_utils.get_region_terminals("South England")
    northern_terminals = factory.geographic_utils.get_region_terminals("Scotland")

    if from_region == "South England" and to_region == "Scotland":
        southern_terminus = factory.geographic_utils.find_best_terminus_for_station(
            from_station, southern_terminals, factory.data_repository
        )
        northern_terminus = factory.geographic_utils.find_best_terminus_for_station(
            to_station, northern_terminals, factory.data_repository
        )
        london_from, london_to = factory.geographic_utils.find_best_london_connection(
            southern_terminus, northern_terminus
        )

        segments: list[RouteSegment] = []

        if from_station != southern_terminus:
            segments.append(
                factory._create_national_rail_segment(
                    from_station,
                    southern_terminus,
                    factory.journey_estimator.get_line_between_stations(
                        from_station, southern_terminus, factory.data_repository
                    ),
                )
            )

        segments.append(
            RouteSegment(
                from_station=london_from,
                to_station=london_to,
                line_name="London Underground",
                distance_km=factory.journey_estimator.estimate_underground_distance(
                    london_from, london_to, "london"
                ),
                journey_time_minutes=factory.journey_estimator.estimate_underground_time(
                    london_from, london_to, "london"
                ),
                service_pattern="UNDERGROUND",
                train_service_id="LONDON_UNDERGROUND_SERVICE",
            )
        )

        segments.append(
            factory._create_national_rail_segment(
                london_to,
                northern_terminus,
                factory.journey_estimator.get_line_between_stations(
                    london_to, northern_terminus, factory.data_repository
                ),
            )
        )

        if to_station != northern_terminus:
            system_info = factory.station_classifier.get_underground_system(to_station)
            if system_info:
                system_key, system_name = system_info
                segments.append(
                    RouteSegment(
                        from_station=northern_terminus,
                        to_station=to_station,
                        line_name=system_name,
                        distance_km=factory.journey_estimator.estimate_underground_distance(
                            northern_terminus, to_station, system_key
                        ),
                        journey_time_minutes=factory.journey_estimator.estimate_underground_time(
                            northern_terminus, to_station, system_key
                        ),
                        service_pattern="UNDERGROUND",
                        train_service_id=f"{system_key.upper()}_UNDERGROUND_SERVICE",
                    )
                )

        total_distance = sum(segment.distance_km or 0 for segment in segments)
        total_time = sum(segment.journey_time_minutes or 0 for segment in segments)
        changes_required = len(segments) - 1

        full_path: list[str] = [from_station] if from_station == southern_terminus else [from_station, southern_terminus]
        if london_from != southern_terminus:
            full_path.append(london_from)
        if london_to != london_from:
            full_path.append(london_to)
        if northern_terminus != london_to:
            full_path.append(northern_terminus)
        if to_station != northern_terminus:
            full_path.append(to_station)

        return Route(
            from_station=from_station,
            to_station=to_station,
            segments=segments,
            total_distance_km=total_distance,
            total_journey_time_minutes=total_time,
            changes_required=changes_required,
            full_path=full_path,
        )

    if from_region == "Scotland" and to_region == "South England":
        northern_terminus = factory.geographic_utils.find_best_terminus_for_station(
            from_station, northern_terminals, factory.data_repository
        )
        southern_terminus = factory.geographic_utils.find_best_terminus_for_station(
            to_station, southern_terminals, factory.data_repository
        )
        london_from, london_to = factory.geographic_utils.find_best_london_connection(
            northern_terminus, southern_terminus
        )

        segments: list[RouteSegment] = []

        if from_station != northern_terminus:
            system_info = factory.station_classifier.get_underground_system(from_station)
            if system_info:
                system_key, system_name = system_info
                segments.append(
                    RouteSegment(
                        from_station=from_station,
                        to_station=northern_terminus,
                        line_name=system_name,
                        distance_km=factory.journey_estimator.estimate_underground_distance(
                            from_station, northern_terminus, system_key
                        ),
                        journey_time_minutes=factory.journey_estimator.estimate_underground_time(
                            from_station, northern_terminus, system_key
                        ),
                        service_pattern="UNDERGROUND",
                        train_service_id=f"{system_key.upper()}_UNDERGROUND_SERVICE",
                    )
                )

        segments.append(
            factory._create_national_rail_segment(
                northern_terminus if segments else from_station,
                london_from,
                factory.journey_estimator.get_line_between_stations(
                    northern_terminus if segments else from_station,
                    london_from,
                    factory.data_repository,
                ),
            )
        )

        segments.append(
            RouteSegment(
                from_station=london_from,
                to_station=london_to,
                line_name="London Underground",
                distance_km=factory.journey_estimator.estimate_underground_distance(
                    london_from, london_to, "london"
                ),
                journey_time_minutes=factory.journey_estimator.estimate_underground_time(
                    london_from, london_to, "london"
                ),
                service_pattern="UNDERGROUND",
                train_service_id="LONDON_UNDERGROUND_SERVICE",
            )
        )

        segments.append(
            factory._create_national_rail_segment(
                london_to,
                southern_terminus,
                factory.journey_estimator.get_line_between_stations(
                    london_to, southern_terminus, factory.data_repository
                ),
            )
        )

        if to_station != southern_terminus:
            segments.append(
                factory._create_national_rail_segment(
                    southern_terminus,
                    to_station,
                    factory.journey_estimator.get_line_between_stations(
                        southern_terminus, to_station, factory.data_repository
                    ),
                )
            )

        total_distance = sum(segment.distance_km or 0 for segment in segments)
        total_time = sum(segment.journey_time_minutes or 0 for segment in segments)
        changes_required = len(segments) - 1

        full_path: list[str] = [from_station] if from_station == northern_terminus else [from_station, northern_terminus]
        if london_from != northern_terminus:
            full_path.append(london_from)
        if london_to != london_from:
            full_path.append(london_to)
        if southern_terminus != london_to:
            full_path.append(southern_terminus)
        if to_station != southern_terminus:
            full_path.append(to_station)

        return Route(
            from_station=from_station,
            to_station=to_station,
            segments=segments,
            total_distance_km=total_distance,
            total_journey_time_minutes=total_time,
            changes_required=changes_required,
            full_path=full_path,
        )

    return None


"""Routing composition helpers.

Phase 2 boundary:
  - Only the application bootstrap may assemble the object graph.
  - This module provides *pure construction helpers* that bootstrap may call.
  - No module-level singletons.

The public surface is intentionally small to prevent reintroducing hidden
composition across the codebase.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.core.interfaces import IDataRepository, IRouteService, IStationService

from .json_data_repository import JsonDataRepository
from .route_service_refactored import RouteServiceRefactored
from .station_service import StationService


@dataclass(frozen=True)
class RoutingServices:
    """Concrete routing services assembled by bootstrap."""

    data_repository: IDataRepository
    station_service: IStationService
    route_service: IRouteService


def build_routing_services(*, data_directory: str | Path | None = None) -> RoutingServices:
    """Construct the routing object graph.

    Args:
        data_directory: Optional data directory override. When omitted, the
            repository's default resolver is used.

    Returns:
        A fully constructed set of routing services.
    """

    repo = JsonDataRepository(data_directory=str(data_directory) if data_directory else None)
    station_service = StationService(repo)
    route_service = RouteServiceRefactored(repo)
    return RoutingServices(
        data_repository=repo,
        station_service=station_service,
        route_service=route_service,
    )


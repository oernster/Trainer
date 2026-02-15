"""Routing services package.

Phase 2 boundary:
  - No *new* module-level singletons.
  - Bootstrapping/composition happens in `src.services.routing.composition`.
"""

from .json_data_repository import JsonDataRepository
from .station_service import StationService
from .route_service_refactored import RouteServiceRefactored as RouteService

from .composition import RoutingServices, build_routing_services
# Underground services removed

__all__ = [
    'JsonDataRepository',
    'StationService',
    'RouteService',
    'RoutingServices',
    'build_routing_services',
]

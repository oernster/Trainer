"""Core package.

Phase 2 boundary:
  - `src.core` contains ONLY pure domain models + interfaces.
  - All routing/service orchestration lives outside core (see `src.services.routing`).
"""

# Interfaces (ports)
from .interfaces import IDataRepository, IRouteService, IStationService

# Models (domain)
from .models import LineStatus, LineType, RailwayLine, Route, RouteSegment, Station

__all__ = [
    # Interfaces
    'IStationService',
    'IRouteService',
    'IDataRepository',
    
    # Models
    'Station',
    'Route',
    'RouteSegment',
    'RailwayLine',
    'LineType',
    'LineStatus',
]

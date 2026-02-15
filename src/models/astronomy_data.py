"""Backwards-compatible astronomy models.

Historically this project defined all astronomy models in one module.
To satisfy the <=400 LOC quality gate, the implementation is split into:

- [`src/models/astronomy_event_models.py`](src/models/astronomy_event_models.py:1)
- [`src/models/astronomy_daily_models.py`](src/models/astronomy_daily_models.py:1)
- [`src/models/astronomy_forecast_models.py`](src/models/astronomy_forecast_models.py:1)
- [`src/models/astronomy_icon_strategies.py`](src/models/astronomy_icon_strategies.py:1)
- [`src/models/astronomy_validation.py`](src/models/astronomy_validation.py:1)

This file re-exports the public surface for existing imports.
"""

from __future__ import annotations

from .astronomy_daily_models import AstronomyData
from .astronomy_event_models import (
    AstronomyDataReader,
    AstronomyEvent,
    AstronomyEventPriority,
    AstronomyEventType,
    AstronomyIconProvider,
    MoonPhase,
)
from .astronomy_forecast_models import AstronomyForecastData, Location
from .astronomy_icon_strategies import (
    AstronomyIconProviderImpl,
    AstronomyIconStrategy,
    EmojiAstronomyIconStrategy,
    default_astronomy_icon_provider,
)
from .astronomy_validation import AstronomyDataValidator

__all__ = [
    "AstronomyData",
    "AstronomyDataReader",
    "AstronomyEvent",
    "AstronomyEventPriority",
    "AstronomyEventType",
    "AstronomyForecastData",
    "AstronomyIconProvider",
    "AstronomyIconProviderImpl",
    "AstronomyIconStrategy",
    "AstronomyDataValidator",
    "EmojiAstronomyIconStrategy",
    "Location",
    "MoonPhase",
    "default_astronomy_icon_provider",
]


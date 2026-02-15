"""Strategy-based astronomy icon provider."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from .astronomy_event_models import AstronomyEventType

logger = logging.getLogger(__name__)


class AstronomyIconStrategy(ABC):
    """Abstract strategy for astronomy icon display."""

    @abstractmethod
    def get_icon(self, event_type: AstronomyEventType) -> str: ...

    @abstractmethod
    def get_strategy_name(self) -> str: ...


class EmojiAstronomyIconStrategy(AstronomyIconStrategy):
    """Strategy using emoji icons for astronomy event display."""

    ASTRONOMY_ICONS = {
        AstronomyEventType.APOD: "🌌",
        AstronomyEventType.ISS_PASS: "🚀",
        AstronomyEventType.NEAR_EARTH_OBJECT: "💫",
        AstronomyEventType.MOON_PHASE: "🌕",
        AstronomyEventType.PLANETARY_EVENT: "🌟",
        AstronomyEventType.METEOR_SHOWER: "✨",
        AstronomyEventType.SOLAR_EVENT: "🌞",
        AstronomyEventType.SATELLITE_IMAGE: "🛰️",
        AstronomyEventType.UNKNOWN: "❓",
    }

    def get_icon(self, event_type: AstronomyEventType) -> str:
        return self.ASTRONOMY_ICONS.get(event_type, "❓")

    def get_strategy_name(self) -> str:
        return "emoji"


class AstronomyIconProviderImpl:
    """Context class for astronomy icon strategies."""

    def __init__(self, strategy: AstronomyIconStrategy):
        self._strategy = strategy
        logger.info(
            "AstronomyIconProvider initialized with %s strategy",
            strategy.get_strategy_name(),
        )

    def set_strategy(self, strategy: AstronomyIconStrategy) -> None:
        old_strategy = self._strategy.get_strategy_name()
        self._strategy = strategy
        logger.info(
            "Astronomy icon strategy changed from %s to %s",
            old_strategy,
            strategy.get_strategy_name(),
        )

    def get_astronomy_icon(self, event_type: AstronomyEventType) -> str:
        return self._strategy.get_icon(event_type)

    def get_current_strategy_name(self) -> str:
        return self._strategy.get_strategy_name()


default_astronomy_icon_provider = AstronomyIconProviderImpl(EmojiAstronomyIconStrategy())


__all__ = [
    "AstronomyIconProviderImpl",
    "AstronomyIconStrategy",
    "EmojiAstronomyIconStrategy",
    "default_astronomy_icon_provider",
]


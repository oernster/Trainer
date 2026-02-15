"""Factory helpers for creating [`AstronomyManager`](src/managers/astronomy_manager.py:34).

Split out to keep modules under the <= 400 non-blank LOC gate.
"""

from __future__ import annotations

from .astronomy_config import AstronomyConfig


class AstronomyManagerFactory:
    """Factory for creating astronomy managers."""

    @staticmethod
    def create_manager(config: AstronomyConfig):
        """Create astronomy manager with given configuration."""
        from .astronomy_manager import AstronomyManager

        return AstronomyManager(config)

    @staticmethod
    def create_disabled_manager():
        """Create a disabled astronomy manager for testing."""
        from .astronomy_manager import AstronomyManager

        config = AstronomyConfig(enabled=False)
        return AstronomyManager(config)

    @staticmethod
    def create_test_manager(api_key: str = "test_key"):
        """Create astronomy manager for testing."""

        # `api_key` kept for backwards compatibility with older tests/callers.
        _ = api_key

        from .astronomy_manager import AstronomyManager

        config = AstronomyConfig(
            enabled=True,
            location_name="Test Location",
            location_latitude=51.5074,
            location_longitude=-0.1278,
        )
        return AstronomyManager(config)


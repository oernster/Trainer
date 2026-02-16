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
        # Phase 2 directive: factories must not assemble the object graph.
        # Composition root must inject `AstronomyManager`.
        raise RuntimeError(
            "AstronomyManagerFactory is not allowed to compose AstronomyManager in Phase 2; "
            "use src.app.bootstrap.bootstrap_app()"
        )

    @staticmethod
    def create_disabled_manager():
        """Create a disabled astronomy manager for testing."""
        # Tests should construct managers explicitly (or use bootstrap) in Phase 2.
        raise RuntimeError(
            "AstronomyManagerFactory is not allowed to compose AstronomyManager in Phase 2; "
            "construct explicitly in tests"
        )

    @staticmethod
    def create_test_manager(api_key: str = "test_key"):
        """Create astronomy manager for testing."""

        # `api_key` kept for backwards compatibility with older tests/callers.
        _ = api_key

        raise RuntimeError(
            "AstronomyManagerFactory is not allowed to compose AstronomyManager in Phase 2; "
            "construct explicitly in tests"
        )


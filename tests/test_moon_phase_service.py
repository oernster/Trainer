from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.models.astronomy_data import MoonPhase
from src.services.moon_phase_service import EnhancedMoonPhaseCalculator


@pytest.fixture()
def calc() -> EnhancedMoonPhaseCalculator:
    return EnhancedMoonPhaseCalculator()


@pytest.mark.parametrize(
    "dt, expected_phase",
    [
        # Epoch new moon used by the algorithm
        (datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc), MoonPhase.NEW_MOON),
        # Quarter phases based on synodic month fraction
        (datetime(2000, 1, 14, 1, 55, tzinfo=timezone.utc), MoonPhase.FIRST_QUARTER),
        (datetime(2000, 1, 21, 9, 36, tzinfo=timezone.utc), MoonPhase.FULL_MOON),
        (datetime(2000, 1, 28, 17, 17, tzinfo=timezone.utc), MoonPhase.LAST_QUARTER),
    ],
)
def test_known_phase_moments(calc: EnhancedMoonPhaseCalculator, dt: datetime, expected_phase: MoonPhase):
    phase, illumination = calc.calculate_moon_phase(dt)
    assert phase == expected_phase
    assert 0.0 <= illumination <= 1.0


def test_full_moon_is_not_reported_as_new_moon(calc: EnhancedMoonPhaseCalculator):
    # Regression guard: the reported issue was "full moon outside" but UI showed new moon.
    # We use a full-moon moment from the known-phase set above.
    dt = datetime(2000, 1, 21, 9, 36, tzinfo=timezone.utc)
    phase, _ = calc.calculate_moon_phase(dt)
    assert phase != MoonPhase.NEW_MOON


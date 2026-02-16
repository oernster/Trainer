from __future__ import annotations

from pathlib import Path


def test_weather_startup_triggers_initial_refresh() -> None:
    """Guard against the "blank weather for 30 minutes" regression.

    Root cause was that the refactor removed the one-shot startup fetch from the
    initialization sequence, leaving only WeatherManager's 30-minute timer.

    This test stays Qt-free by asserting the composition-root startup code
    schedules an initial refresh.
    """

    repo_root = Path(__file__).resolve().parents[1]
    main_py = (repo_root / "main.py").read_text(encoding="utf-8", errors="replace")

    # Keep this intentionally simple and resilient to refactors.
    assert "window.refresh_weather()" in main_py


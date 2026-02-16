from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


class _Signal:
    def __init__(self) -> None:
        self.emissions: list[tuple[Any, ...]] = []

    def emit(self, *args: Any) -> None:
        self.emissions.append(tuple(args))


@dataclass
class _FakeConfigService:
    valid: bool = False

    def has_valid_station_config(self) -> bool:
        return self.valid

    def set_route_path(self, *_args: Any, **_kwargs: Any) -> None:
        return None


def test_fetch_trains_emits_empty_results_synchronously_when_no_config(monkeypatch):
    """Regression test for splash hangs on fresh installs.

    If there is no station config, TrainManager should emit the empty results
    immediately on the calling (main) thread, rather than spinning up a thread
    and relying on Qt cross-thread signal delivery during startup.
    """

    # Import here so the test doesn't require Qt at import time for collection.
    from src.managers.train_manager import TrainManager

    # Construct a TrainManager instance without running QObject/QThread machinery.
    tm = TrainManager.__new__(TrainManager)
    tm.current_trains = []
    tm.last_update = None
    tm.is_fetching = False
    tm._fetch_queue = None
    tm._queue_lock = None
    tm._fetch_lock = None

    tm.configuration_service = _FakeConfigService(valid=False)

    tm.trains_updated = _Signal()
    tm.connection_changed = _Signal()
    tm.last_update_changed = _Signal()
    tm.status_changed = _Signal()

    # Ensure we don't attempt to use threading locks / queues when the fast-path triggers.
    def _boom(*_a: Any, **_kw: Any) -> None:
        raise AssertionError("Async path should not be used when no station config")

    monkeypatch.setattr(tm, "_process_fetch_queue", _boom, raising=False)
    monkeypatch.setattr(tm, "_start_async_fetch", _boom, raising=False)

    tm.fetch_trains()

    assert tm.trains_updated.emissions == [([],)], (
        "Expected trains_updated to be emitted with an empty list when no station config"
    )
    assert tm.status_changed.emissions, "Expected a status update to be emitted"

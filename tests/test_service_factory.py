from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

import src.core.services.service_factory as sf


class _Repo:
    def __init__(self):
        self.refreshed = False

    def refresh_data(self) -> bool:
        self.refreshed = True
        return True

    def get_network_statistics(self):
        return {"total_stations": 1, "total_lines": 2}

    def load_stations(self):
        return [object()]


class _StationService:
    def __init__(self):
        self.cleared = False

    def clear_cache(self) -> None:
        self.cleared = True

    def get_station_suggestions(self, _query: str, limit: int = 5):
        return ["X"] * min(limit, 1)

    def get_station_statistics(self):
        return {"stations": 1}


class _RouteService:
    def __init__(self):
        self.cleared = False
        self.precomputed = None

    def clear_route_cache(self) -> None:
        self.cleared = True

    def get_route_statistics(self):
        return {"routes": 0}

    def precompute_common_routes(self, station_pairs):
        self.precomputed = list(station_pairs)

    def calculate_route(self, _a: str, _b: str):
        return object()


def test_service_factory_default_data_directory_fallback(monkeypatch, tmp_path: Path):
    # Force resolver import to fail to hit fallback Path(__file__).parents ... / data
    def _raise(*_a, **_k):
        raise ImportError("no")

    monkeypatch.setattr(sf, "get_data_directory", _raise, raising=False)
    f = sf.ServiceFactory(data_directory=None)
    assert f.data_directory


def test_service_factory_refresh_and_shutdown(monkeypatch, tmp_path: Path):
    f = sf.ServiceFactory(data_directory=str(tmp_path))
    repo = _Repo()
    station = _StationService()
    route = _RouteService()
    f._data_repository = cast(Any, repo)
    f._station_service = cast(Any, station)
    f._route_service = cast(Any, route)

    assert f.refresh_all_services() is True
    assert repo.refreshed is True
    assert station.cleared is True
    assert route.cleared is True

    f.shutdown()
    assert f._data_repository is None
    assert f._station_service is None
    assert f._route_service is None


def test_service_factory_get_service_statistics(monkeypatch, tmp_path: Path):
    f = sf.ServiceFactory(data_directory=str(tmp_path))
    f._data_repository = cast(Any, _Repo())
    f._station_service = cast(Any, _StationService())
    f._route_service = cast(Any, _RouteService())

    stats = f.get_service_statistics()
    assert "data_repository" in stats
    assert "station_service" in stats
    assert "route_service" in stats


def test_service_factory_get_service_statistics_handles_exception(monkeypatch, tmp_path: Path):
    f = sf.ServiceFactory(data_directory=str(tmp_path))

    class _BadRepo:
        def get_network_statistics(self):
            raise RuntimeError("boom")

    f._data_repository = cast(Any, _BadRepo())
    stats = f.get_service_statistics()
    assert "error" in stats


def test_service_factory_precompute_common_routes(monkeypatch, tmp_path: Path):
    f = sf.ServiceFactory(data_directory=str(tmp_path))
    route = _RouteService()
    f._route_service = cast(Any, route)
    f.precompute_common_routes([("A", "B")])
    assert route.precomputed == [("A", "B")]


def test_service_factory_validate_services_success(monkeypatch, tmp_path: Path):
    f = sf.ServiceFactory(data_directory=str(tmp_path))

    # Monkeypatch constructors used by getters so validate_services doesn't touch real data.
    monkeypatch.setattr(sf, "JsonDataRepository", lambda _p: _Repo())
    monkeypatch.setattr(sf, "StationService", lambda _r: _StationService())
    monkeypatch.setattr(sf, "RouteServiceRefactored", lambda _r: _RouteService())

    results = f.validate_services()
    assert results["data_repository"] is True
    assert results["station_service"] is True
    assert results["route_service"] is True


def test_service_factory_validate_services_handles_exception(monkeypatch, tmp_path: Path):
    f = sf.ServiceFactory(data_directory=str(tmp_path))

    def _boom(_p):
        raise RuntimeError("boom")

    monkeypatch.setattr(sf, "JsonDataRepository", _boom)
    results = f.validate_services()
    assert "error" in results


def test_service_factory_module_singletons(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(sf, "_service_factory", None)
    f1 = sf.get_service_factory(data_directory=str(tmp_path))
    f2 = sf.get_service_factory(data_directory=str(tmp_path / "other"))
    assert f1 is f2


from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.cache.station_cache_manager import StationCacheManager


def test_station_cache_manager_init_defaults_to_module_dir(tmp_path: Path, monkeypatch):
    # Force __file__ to a temp location so default cache_directory resolves there.
    fake_module_dir = tmp_path / "cache"
    fake_module_dir.mkdir(parents=True)
    monkeypatch.setattr(
        "src.cache.station_cache_manager.__file__",
        str(fake_module_dir / "station_cache_manager.py"),
    )

    mgr = StationCacheManager(cache_directory=None)
    assert mgr.cache_directory == fake_module_dir
    assert mgr.station_cache_file == fake_module_dir / "station_data.cache"
    assert mgr.metadata_file == fake_module_dir / "cache_metadata.json"


def test_station_cache_manager_save_and_load_roundtrip(tmp_path: Path):
    mgr = StationCacheManager(cache_directory=str(tmp_path))
    stations = ["B", "A", "C"]
    assert mgr.save_stations_to_cache(stations) is True

    loaded = mgr.load_cached_stations()
    assert loaded == ["A", "B", "C"]


def test_station_cache_manager_is_cache_valid_checks_version_and_age(tmp_path: Path, monkeypatch):
    mgr = StationCacheManager(cache_directory=str(tmp_path))
    assert mgr.save_stations_to_cache(["A"]) is True
    assert mgr.is_cache_valid() is True

    # Corrupt version.
    bad_meta = mgr._load_cache_metadata()
    bad_meta["cache_version"] = "0"
    assert mgr._save_cache_metadata(bad_meta) is True
    assert mgr.is_cache_valid() is False

    # Restore version and force expiration by setting created_timestamp far in the past.
    bad_meta["cache_version"] = mgr.cache_version
    bad_meta["created_timestamp"] = "2000-01-01T00:00:00"
    assert mgr._save_cache_metadata(bad_meta) is True
    assert mgr.is_cache_valid() is False


def test_station_cache_manager_is_cache_valid_detects_data_source_change(tmp_path: Path):
    mgr = StationCacheManager(cache_directory=str(tmp_path))
    data_dir = tmp_path / "data"
    (data_dir / "lines").mkdir(parents=True)
    (data_dir / "railway_lines_index_comprehensive.json").write_text("{}", encoding="utf-8")
    (data_dir / "uk_underground_stations.json").write_text("{}", encoding="utf-8")
    (data_dir / "lines" / "a.json").write_text("{}", encoding="utf-8")

    assert mgr.save_stations_to_cache(["A"], data_directory=data_dir) is True
    assert mgr.is_cache_valid(data_dir) is True

    # Change the data source by touching a line file.
    (data_dir / "lines" / "a.json").write_text("{\"changed\": true}", encoding="utf-8")
    assert mgr.is_cache_valid(data_dir) is False


def test_station_cache_manager_load_returns_none_when_missing(tmp_path: Path):
    mgr = StationCacheManager(cache_directory=str(tmp_path))
    assert mgr.load_cached_stations() is None


def test_station_cache_manager_load_handles_corrupt_cache(tmp_path: Path):
    mgr = StationCacheManager(cache_directory=str(tmp_path))
    mgr.station_cache_file.write_bytes(b"not json")
    assert mgr.load_cached_stations() is None


def test_station_cache_manager_save_metadata_failure_returns_false(tmp_path: Path, monkeypatch):
    mgr = StationCacheManager(cache_directory=str(tmp_path))

    def _boom(*_args, **_kwargs):
        raise OSError("nope")

    monkeypatch.setattr(json, "dump", _boom)
    assert mgr._save_cache_metadata({"x": 1}) is False


def test_station_cache_manager_clear_cache_removes_files(tmp_path: Path):
    mgr = StationCacheManager(cache_directory=str(tmp_path))
    assert mgr.save_stations_to_cache(["A"]) is True
    assert mgr.station_cache_file.exists()
    assert mgr.metadata_file.exists()

    assert mgr.clear_cache() is True
    assert not mgr.station_cache_file.exists()
    assert not mgr.metadata_file.exists()


def test_station_cache_manager_get_cache_info_contains_expected_fields(tmp_path: Path):
    mgr = StationCacheManager(cache_directory=str(tmp_path))
    info = mgr.get_cache_info()
    assert info["cache_directory"] == str(tmp_path)
    assert info["cache_version"] == mgr.cache_version
    assert "cache_file_exists" in info
    assert "metadata_file_exists" in info


def test_station_cache_manager_optimize_cache_no_data_returns_false(tmp_path: Path, caplog):
    mgr = StationCacheManager(cache_directory=str(tmp_path))
    assert mgr.optimize_cache() is False
    assert any("No cached data to optimize" in r.message for r in caplog.records)


def test_station_cache_manager_is_constructible_multiple_times(tmp_path: Path):
    # Phase 2 boundary: no module-level singleton accessors; composition root owns lifetime.
    m1 = StationCacheManager(cache_directory=str(tmp_path))
    m2 = StationCacheManager(cache_directory=str(tmp_path / "other"))
    assert m1 is not m2


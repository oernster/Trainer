from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.managers.simple_route_finder import SimpleRouteFinder


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def test_simple_route_finder_load_data_and_direct_routes(tmp_path: Path, monkeypatch):
    data_dir = tmp_path / "data"
    lines_dir = data_dir / "lines"
    lines_dir.mkdir(parents=True)

    _write_json(
        data_dir / "railway_lines_index.json",
        {
            "lines": [
                {"name": "L1", "file": "l1.json"},
                {"name": "L2", "file": "l2.json"},
            ]
        },
    )

    _write_json(
        lines_dir / "l1.json",
        {"stations": [{"name": "A"}, {"name": "B"}, {"name": "C"}]},
    )
    _write_json(
        lines_dir / "l2.json",
        {"stations": [{"name": "B"}, {"name": "D"}]},
    )

    f = SimpleRouteFinder()
    f.data_dir = data_dir
    f.lines_dir = lines_dir

    assert f.load_data() is True
    assert f.loaded is True

    assert f.find_direct_route("A", "C") == ["A", "B", "C"]
    assert f.find_direct_route("C", "A") == ["C", "B", "A"]
    assert f.find_direct_route("A", "D") is None


def test_simple_route_finder_load_data_missing_index_returns_false(tmp_path: Path):
    f = SimpleRouteFinder()
    f.data_dir = tmp_path
    f.lines_dir = tmp_path / "lines"
    assert f.load_data() is False


def test_simple_route_finder_getters_trigger_load_and_handle_failure(tmp_path: Path):
    f = SimpleRouteFinder()
    f.data_dir = tmp_path
    f.lines_dir = tmp_path / "lines"

    assert f.get_all_stations() == []
    assert f.get_lines_for_station("A") == []
    assert f.get_stations_on_line("L") == []
    assert f.find_interchange_stations() == []


def test_simple_route_finder_interchanges_and_route_with_changes(tmp_path: Path):
    data_dir = tmp_path / "data"
    lines_dir = data_dir / "lines"
    lines_dir.mkdir(parents=True)

    _write_json(
        data_dir / "railway_lines_index.json",
        {"lines": [{"name": "L1", "file": "l1.json"}, {"name": "L2", "file": "l2.json"}]},
    )
    _write_json(lines_dir / "l1.json", {"stations": [{"name": "A"}, {"name": "X"}]})
    _write_json(lines_dir / "l2.json", {"stations": [{"name": "X"}, {"name": "B"}]})

    f = SimpleRouteFinder()
    f.data_dir = data_dir
    f.lines_dir = lines_dir

    assert f.find_interchange_stations() == ["X"]
    assert f.find_route_with_changes("A", "B", max_changes=0) is None
    assert f.find_route_with_changes("A", "B", max_changes=1) == ["A", "X", "B"]


def test_simple_route_finder_load_data_exception_returns_false(monkeypatch):
    f = SimpleRouteFinder()

    def _boom():
        raise RuntimeError("boom")

    monkeypatch.setattr(f, "load_data", _boom)
    # load_data exception should be handled inside find_direct_route.
    assert f.find_direct_route("A", "B") is None


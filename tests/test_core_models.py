from __future__ import annotations

import pytest

from src.core.models.railway_line import LineStatus, LineType, RailwayLine
from src.core.models.route import Route, RouteSegment
from src.core.models.station import Station


def test_station_validates_and_normalizes_lists():
    with pytest.raises(ValueError, match="Station name cannot be empty"):
        Station(name="  ")

    # Provide tuples to exercise `__post_init__` list normalization.
    s = Station(name="A", interchange=("L1", "L2"), facilities=("toilets",))  # type: ignore[arg-type]
    assert s.interchange == ["L1", "L2"]
    assert s.facilities == ["toilets"]

    assert s.is_interchange is True
    assert s.has_facility("toilets") is True
    assert s.has_facility("wifi") is False
    assert s.get_lines() == ["L1", "L2"]
    assert s.serves_line("L1") is True
    assert s.serves_line("L3") is False


def test_station_properties_and_display_helpers():
    london = Station(name="London Waterloo", zone="1", interchange=["London Underground", "L1", "L2"])
    assert london.is_london_station is True
    assert london.is_major_station is True
    assert london.get_display_name() == "London Waterloo"
    assert london.get_short_name() == "Waterloo"
    assert str(london) == "London Waterloo"
    assert "Station(name='London Waterloo'" in repr(london)

    minor = Station(name="Fleet")
    assert minor.is_london_station is False
    assert minor.is_major_station is False
    assert minor.get_short_name() == "Fleet"

    with pytest.raises(NotImplementedError, match="domain model"):
        minor.is_underground_station()

    with pytest.raises(NotImplementedError, match="domain model"):
        minor.get_underground_system()

    with pytest.raises(NotImplementedError, match="domain model"):
        minor.is_mixed_station()


def test_station_dict_round_trip_includes_computed_fields():
    s = Station(
        name="London Liverpool Street",
        coordinates=(51.5175, -0.0829),
        interchange=["L1", "L2"],
        operator="X",
        zone="1",
        accessibility={"step_free": True},
        facilities=["toilets"],
    )

    d = s.to_dict()
    assert d["name"] == "London Liverpool Street"
    assert d["coordinates"] == (51.5175, -0.0829)
    assert d["interchange"] == ["L1", "L2"]
    assert d["is_interchange"] is True
    assert d["is_london_station"] is True
    assert d["is_major_station"] is True
    assert d["display_name"] == "London Liverpool Street"
    assert d["short_name"]

    restored = Station.from_dict(d)
    assert restored.name == s.name
    assert restored.coordinates == s.coordinates
    assert restored.interchange == s.interchange
    assert restored.facilities == s.facilities


def test_railway_line_validates_and_basic_properties():
    with pytest.raises(ValueError, match="Line name cannot be empty"):
        RailwayLine(name="", stations=["A", "B"])

    with pytest.raises(ValueError, match="at least 2"):
        RailwayLine(name="L", stations=["A"])

    with pytest.raises(ValueError, match="duplicate"):
        RailwayLine(name="L", stations=["A", "A"])

    line = RailwayLine(
        name="L1",
        stations=["A", "B", "C"],
        line_type=LineType.MAINLINE,
        status=LineStatus.ACTIVE,
        journey_times={"A-B": 10},
        distances={"A": {"B": 1.2}, "B": {"C": 1.0}, "C": {}},
    )

    assert line.station_count == 3
    assert line.is_active is True
    assert line.is_branch_line is False
    assert line.is_mainline is True
    assert line.terminus_stations == ["A", "C"]
    assert line.intermediate_stations == ["B"]
    assert line.has_station("B") is True
    assert line.get_station_index("B") == 1
    assert line.get_station_index("Z") is None
    assert line.get_adjacent_stations("A") == ["B"]
    assert line.get_adjacent_stations("B") == ["A", "C"]
    assert line.get_adjacent_stations("C") == ["B"]
    assert line.get_adjacent_stations("Z") == []
    assert line.get_stations_between("A", "C") == ["B"]
    assert line.get_stations_between("C", "A") == ["B"]
    assert line.get_stations_between("A", "Z") == []
    assert line.get_journey_time("A", "B") == 10
    assert line.get_journey_time("B", "A") == 10
    assert line.get_journey_time("A", "C") is None
    assert line.get_distance("A", "B") == 1.2
    assert line.get_distance("A", "C") is None
    assert line.is_direct_connection("A", "B") is True
    assert line.is_direct_connection("A", "Z") is False
    assert line.get_direction("A", "C") == "towards C"
    assert line.get_direction("C", "A") == "towards A"
    assert line.get_direction("B", "B") is None
    assert line.get_direction("B", "Z") is None
    assert line.get_stations_in_direction("A", "up") == ["B", "C"]
    assert line.get_stations_in_direction("C", "down") == ["A", "B"]
    assert line.get_stations_in_direction("Z", "up") == []
    assert line.get_stations_in_direction("A", "unknown") == []

    summary = line.get_line_summary()
    assert summary["name"] == "L1"
    assert summary["station_count"] == 3

    as_dict = line.to_dict()
    assert as_dict["stations"] == ["A", "B", "C"]
    # Round-trip
    line2 = RailwayLine.from_dict(as_dict)
    assert line2.name == "L1"
    assert line2.stations == ["A", "B", "C"]
    assert str(line2).startswith("L1")
    assert "RailwayLine(name='L1'" in repr(line2)
    assert ("B" in line2) is True
    assert len(line2) == 3
    assert list(iter(line2)) == ["A", "B", "C"]


def test_railway_line_journey_times_validation_errors():
    with pytest.raises(ValueError, match="from_station 'X' not in line stations"):
        RailwayLine(name="L", stations=["A", "B"], journey_times={"X-A": 10})

    with pytest.raises(ValueError, match="to_station 'X' not in line stations"):
        RailwayLine(name="L", stations=["A", "B"], journey_times={"A-X": 10})

    # No dash key => ignored by validation loop
    RailwayLine(name="L", stations=["A", "B"], journey_times={"AtoB": 10})


def test_railway_line_journey_times_skip_metadata_and_non_numeric_entries():
    # These entries should be ignored by validation, even if their station names
    # would otherwise be invalid.
    RailwayLine(
        name="L",
        stations=["A", "B"],
        journey_times={
            "metadata": {"source": "x"},  # type: ignore[dict-item]
            "A-X": "fast",  # type: ignore[dict-item]
            "A-B": 10,
        },
    )


def test_railway_line_distances_validation_errors():
    with pytest.raises(ValueError, match="from_station 'X' not in line stations"):
        RailwayLine(name="L", stations=["A", "B"], distances={"X": {"A": 1.0}})

    with pytest.raises(ValueError, match="to_station 'X' not in line stations"):
        RailwayLine(name="L", stations=["A", "B"], distances={"A": {"X": 1.0}})


def test_route_segment_validates():
    with pytest.raises(ValueError, match="cannot be empty"):
        RouteSegment(from_station="", to_station="B", line_name="L")

    with pytest.raises(ValueError, match="Line name cannot be empty"):
        RouteSegment(from_station="A", to_station="B", line_name="")


def test_route_validates_and_computes_totals_and_types():
    seg = RouteSegment(from_station="A", to_station="B", line_name="L", journey_time_minutes=10, distance_km=1.0)
    r = Route(from_station="A", to_station="B", segments=[seg])
    assert r.is_direct is True
    assert r.requires_changes is False
    assert r.route_type == "direct"
    assert r.changes_required == 0
    assert r.total_distance_km == 1.0
    assert r.total_journey_time_minutes == 10
    assert r.intermediate_stations == []
    assert r.interchange_stations == []
    assert r.lines_used == ["L"]
    assert r.get_journey_time_display() == "10m"
    assert r.get_distance_display() == "1.0km"
    assert r.get_route_description().startswith("Direct service")
    assert r.get_detailed_description()

    seg2 = RouteSegment(from_station="B", to_station="C", line_name="L2", journey_time_minutes=20, distance_km=2.0)
    r2 = Route(from_station="A", to_station="C", segments=[seg, seg2])
    assert r2.route_type == "interchange"
    assert r2.changes_required == 1
    # adds 5 minutes interchange
    assert r2.total_journey_time_minutes == 10 + 20 + 5
    assert r2.interchange_stations == ["B"]
    assert r2.intermediate_stations == ["B"]
    assert "Change once" in r2.get_route_description()
    assert any("Change to" in step for step in r2.get_detailed_description())

    seg3 = RouteSegment(from_station="C", to_station="D", line_name="L3")
    r3 = Route(from_station="A", to_station="D", segments=[seg, seg2, seg3], total_journey_time_minutes=0)
    assert r3.route_type == "complex"
    assert r3.changes_required == 2
    assert r3.requires_changes is True
    assert r3.get_journey_time_display() == "0m"
    assert "2 changes" in r3.get_route_description()

    # total_distance_km stays None when all distances are None/0
    no_dist = Route(from_station="A", to_station="B", segments=[RouteSegment(from_station="A", to_station="B", line_name="L")])
    assert no_dist.total_distance_km is None

    # total_time stays None when all journey times missing
    assert no_dist.total_journey_time_minutes is None

    # full_path without intermediate
    direct_path = Route(from_station="A", to_station="B", segments=[seg], full_path=["A", "B"])
    assert direct_path.intermediate_stations == []

    # intermediate_stations fallback includes segment endpoints and trims
    seg_a_b = RouteSegment(from_station="A", to_station="B", line_name="L")
    seg_b_c = RouteSegment(from_station="B", to_station="C", line_name="L")
    r_fb = Route(from_station="A", to_station="C", segments=[seg_a_b, seg_b_c])
    assert r_fb.intermediate_stations == ["B"]

    # interchange station branch where stations don't line up
    seg_bad = RouteSegment(from_station="X", to_station="Y", line_name="L")
    r_bad = Route(from_station="A", to_station="Z", segments=[seg_a_b, seg_bad])
    assert r_bad.interchange_stations == []

    # is_underground_route branches
    assert Route(from_station="A", to_station="B", segments=[seg], routing_type="regular").is_underground_route is False
    assert Route(from_station="A", to_station="B", segments=[seg], routing_type="underground").is_underground_route is True

    # get_journey_time_display unknown
    assert no_dist.get_journey_time_display() == "Unknown"

    # get_distance_display unknown
    assert no_dist.get_distance_display() == "Unknown"

    # distance_display meters
    tiny = Route(
        from_station="A",
        to_station="B",
        segments=[RouteSegment(from_station="A", to_station="B", line_name="L", distance_km=0.2)],
        total_distance_km=0.2,
        total_journey_time_minutes=1,
    )
    assert tiny.get_distance_display() == "200m"

    # journey_time_display hours
    long = Route(from_station="A", to_station="B", segments=[seg], total_journey_time_minutes=125)
    assert long.get_journey_time_display() == "2h 5m"


def test_route_description_same_station_path_is_direct_and_non_direct_paths():
    seg = RouteSegment(from_station="A", to_station="B", line_name="L")
    same = Route(from_station="A", to_station="A", segments=[], routing_type="same_station")
    assert same.get_route_description() == "Same station"
    assert same.intermediate_stations == []

    r = Route(from_station="A", to_station="B", segments=[seg])
    assert r.get_route_description() == "Direct service on L"


def test_route_intermediate_stations_fallback_dedupes_segment_from_stations():
    # Force the `segment.from_station not in stations` false-branch.
    seg1 = RouteSegment(from_station="A", to_station="B", line_name="L")
    seg2 = RouteSegment(from_station="A", to_station="C", line_name="L2")
    r = Route(from_station="A", to_station="C", segments=[seg1, seg2])
    assert r.intermediate_stations == []



def test_route_validation_errors_and_dict_round_trip():
    seg = RouteSegment(from_station="A", to_station="B", line_name="L")
    with pytest.raises(ValueError, match="cannot be empty"):
        Route(from_station="", to_station="B", segments=[seg])

    with pytest.raises(ValueError, match="at least one segment"):
        Route(from_station="A", to_station="B", segments=[])

    # Same-station routing explicitly allows empty segments.
    same = Route(from_station="A", to_station="A", segments=[], routing_type="same_station")
    assert same.get_route_description() == "Same station"

    route = Route(from_station="A", to_station="B", segments=[seg], full_path=["A", "X", "B"])
    assert route.intermediate_stations == ["X"]

    d = route.to_dict()
    restored = Route.from_dict(d)
    assert restored.from_station == "A"
    assert restored.to_station == "B"
    assert restored.segments[0].line_name == "L"
    assert str(restored).startswith("A → B")
    assert "Route(from_station='A'" in repr(restored)

    # No intermediate stations when len(stations) <= 2
    short = RailwayLine(name="S", stations=["X", "Y"])
    assert short.intermediate_stations == []
    assert short.terminus_stations == ["X", "Y"]

    # When len(stations) < 2, terminus_stations falls back, but creation prevents it.
    # We still cover the branch by using an object with stations overridden.
    object.__setattr__(short, "stations", ["X"])  # type: ignore[misc]
    assert short.terminus_stations == ["X"]
    object.__setattr__(short, "stations", ["X", "Y"])  # restore

    # get_journey_time returns None when empty
    assert RailwayLine(name="T", stations=["A", "B"]).get_journey_time("A", "B") is None
    assert RailwayLine(name="T", stations=["A", "B"]).get_distance("A", "B") is None


def test_railway_line_find_interchanges_dedupes_and_skips_self():
    l1 = RailwayLine(name="L1", stations=["A", "B", "C"])
    l2 = RailwayLine(name="L2", stations=["X", "B"])
    l3 = RailwayLine(name="L3", stations=["C", "Y", "B"])
    l1_clone = RailwayLine(name="L1", stations=["B", "C"])

    interchanges = l1.find_interchange_stations([l1, l2, l3, l1_clone])
    # Order is by traversal of l1.stations
    assert interchanges == ["B", "C"]

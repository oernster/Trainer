"""Database loading helpers extracted from StationDatabaseManager."""

from __future__ import annotations

import json


def load_database(*, manager) -> bool:
    """Load the railway station database from JSON files."""

    manager.logger.info("Loading railway station database...")

    # Force clear all existing data
    manager.railway_lines.clear()
    manager.all_stations.clear()
    manager.loaded = False

    try:
        index_file = manager.data_dir / "railway_lines_index.json"
        if not index_file.exists():
            manager.logger.error("Railway lines index not found: %s", index_file)
            return False

        with open(index_file, "r", encoding="utf-8") as f:
            index_data = json.load(f)

        lines = index_data.get("lines", [])
        manager.logger.info("Loading %s railway lines...", len(lines))

        for line_info in lines:
            line_name = line_info.get("name", "Unknown")
            line_file_name = line_info.get("file", "unknown.json")
            line_file = manager.lines_dir / line_file_name

            if not line_file.exists():
                manager.logger.warning("Railway line file not found: %s", line_file)
                continue

            try:
                with open(line_file, "r", encoding="utf-8") as f:
                    line_data = json.load(f)
            except Exception as json_error:  # pragma: no cover
                manager.logger.error("JSON loading failed for %s: %s", line_name, json_error)
                continue

            stations = []
            stations_data = line_data.get("stations", [])

            for j, station_data in enumerate(stations_data):
                try:
                    station_name = station_data.get("name", "Unknown")

                    station = manager.Station(
                        name=station_name,
                        coordinates=station_data.get("coordinates", {}),
                        zone=station_data.get("zone"),
                        interchange=station_data.get("interchange"),
                    )
                    stations.append(station)
                    manager.all_stations[station_name] = station

                except Exception as station_error:  # pragma: no cover
                    manager.logger.error(
                        "Error loading station %s in %s: %s",
                        j + 1,
                        line_name,
                        station_error,
                    )
                    continue

            service_patterns = None
            if "service_patterns" in line_data:
                try:
                    service_patterns = manager.ServicePatternSet.from_dict(
                        {
                            "line_name": line_info["name"],
                            "line_type": "suburban",  # Default, will be classified properly
                            "patterns": line_data["service_patterns"],
                            "default_pattern": "fast",  # Default
                        }
                    )
                except Exception as exc:  # pragma: no cover
                    manager.logger.warning(
                        "Failed to load service patterns for %s: %s",
                        line_info.get("name", "Unknown"),
                        exc,
                    )

            railway_line = manager.RailwayLine(
                name=line_info["name"],
                file=line_info["file"],
                operator=line_info["operator"],
                terminus_stations=line_info["terminus_stations"],
                major_stations=line_info["major_stations"],
                stations=stations,
                service_patterns=service_patterns,
            )

            manager.railway_lines[line_info["name"]] = railway_line

        manager.loaded = True
        manager.logger.info(
            "Database loading complete: %s railway lines, %s stations",
            len(manager.railway_lines),
            len(manager.all_stations),
        )

        key_stations = ["Farnborough (Main)", "London Waterloo", "Fleet", "Woking"]
        missing_stations = [s for s in key_stations if s not in manager.all_stations]
        if missing_stations:
            manager.logger.warning("Missing key stations: %s", missing_stations)
        else:
            manager.logger.debug("All key stations loaded successfully")

        manager.logger.debug("Running database integrity test...")
        if not manager._test_database_integrity():
            manager.logger.error("Database integrity test failed")
            return False

        return True

    except Exception as exc:  # pragma: no cover
        manager.logger.error("Failed to load station database: %s", exc)
        return False


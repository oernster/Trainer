"""
Underground Data Loader

Handles loading and caching of underground system data from JSON files.
"""

import logging
import json
from typing import Dict, Optional, Set
from pathlib import Path


class UndergroundDataLoader:
    """Handles loading and caching of underground system data."""
    
    def __init__(self):
        """Initialize the underground data loader."""
        self.logger = logging.getLogger(__name__)
        
        # Cache for underground station data
        self._london_underground_stations: Optional[Set[str]] = None
        self._glasgow_subway_stations: Optional[Set[str]] = None
        self._tyne_wear_metro_stations: Optional[Set[str]] = None
        
        # Cache for system metadata
        self._underground_systems: Optional[Dict[str, Dict]] = None
    
    def load_underground_systems(self) -> Dict[str, Dict]:
        """Load all underground systems data from properly structured JSON file."""
        if self._underground_systems is not None:
            return self._underground_systems
        
        self._underground_systems = {}
        
        # Load all UK underground stations from properly structured file
        uk_underground_data = self._load_system_data("uk_underground_stations.json", "UK Underground Systems")
        if uk_underground_data:
            # Extract each system from the structured JSON
            london_data = uk_underground_data.get("London Underground", {})
            glasgow_data = uk_underground_data.get("Glasgow Subway", {})
            tyne_wear_data = uk_underground_data.get("Tyne and Wear Metro", {})
            
            # Create system data structures using the JSON data
            if london_data:
                london_stations = set(london_data.get("stations", []))
                self._underground_systems["london"] = {
                    "metadata": {
                        "system": london_data.get("system_name", "London Underground"),
                        "operator": london_data.get("operator", "Transport for London")
                    },
                    "stations": list(london_stations),
                    "terminals": london_data.get("terminals", [])
                }
                self._london_underground_stations = london_stations
            
            if glasgow_data:
                glasgow_stations = set(glasgow_data.get("stations", []))
                self._underground_systems["glasgow"] = {
                    "metadata": {
                        "system": glasgow_data.get("system_name", "Glasgow Subway"),
                        "operator": glasgow_data.get("operator", "Strathclyde Partnership for Transport")
                    },
                    "stations": list(glasgow_stations),
                    "terminals": glasgow_data.get("terminals", [])
                }
                self._glasgow_subway_stations = glasgow_stations
            
            if tyne_wear_data:
                tyne_wear_stations = set(tyne_wear_data.get("stations", []))
                self._underground_systems["tyne_wear"] = {
                    "metadata": {
                        "system": tyne_wear_data.get("system_name", "Tyne and Wear Metro"),
                        "operator": tyne_wear_data.get("operator", "Nexus")
                    },
                    "stations": list(tyne_wear_stations),
                    "terminals": tyne_wear_data.get("terminals", [])
                }
                self._tyne_wear_metro_stations = tyne_wear_stations
        
        return self._underground_systems
    
    def _load_system_data(self, filename: str, system_name: str) -> Optional[Dict]:
        """Load data for a specific underground system."""
        try:
            # Prefer the central resolver, which supports development + packaged
            # environments (including Nuitka app bundles).
            try:
                from ....utils.data_path_resolver import get_data_file_path

                system_file = get_data_file_path(filename)
            except Exception:
                system_file = None

            # Fallbacks for legacy layouts.
            if system_file is None or not system_file.exists():
                possible_paths = [
                    Path(f"data/{filename}"),
                    Path(f"src/data/{filename}"),
                    Path(__file__).parent.parent.parent.parent / "data" / filename,
                ]

                system_file = next((p for p in possible_paths if p.exists()), None)

            if not system_file or not Path(system_file).exists():
                self.logger.warning(f"{system_name} stations file not found: {filename}")
                return None

            with open(Path(system_file), "r", encoding="utf-8") as f:
                data = json.load(f)
            
            stations = data.get('stations', [])
            self.logger.info(f"Loaded {len(stations)} {system_name} stations")
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to load {system_name} stations: {e}")
            return None
    
    def load_london_underground_stations(self) -> Set[str]:
        """Load the list of London Underground stations from JSON file."""
        if self._london_underground_stations is not None:
            return self._london_underground_stations
        
        self.load_underground_systems()
        return self._london_underground_stations or set()
    
    def load_glasgow_subway_stations(self) -> Set[str]:
        """Load the list of Glasgow Subway stations from JSON file."""
        if self._glasgow_subway_stations is not None:
            return self._glasgow_subway_stations
        
        self.load_underground_systems()
        return self._glasgow_subway_stations or set()
    
    def load_tyne_wear_metro_stations(self) -> Set[str]:
        """Load the list of Tyne and Wear Metro stations from JSON file."""
        if self._tyne_wear_metro_stations is not None:
            return self._tyne_wear_metro_stations
        
        self.load_underground_systems()
        return self._tyne_wear_metro_stations or set()
    
    def _load_cross_country_data(self) -> Dict:
        """Load cross-country line data from JSON file."""
        try:
            try:
                from ....utils.data_path_resolver import get_line_file_path

                cross_country_file = get_line_file_path("cross_country_line.json")
            except Exception:
                cross_country_file = None

            if not cross_country_file or not Path(cross_country_file).exists():
                possible_paths = [
                    Path("data/lines/cross_country_line.json"),
                    Path("src/data/lines/cross_country_line.json"),
                    Path(__file__).parent.parent.parent.parent
                    / "data"
                    / "lines"
                    / "cross_country_line.json",
                ]
                cross_country_file = next((p for p in possible_paths if p.exists()), None)

            if not cross_country_file or not Path(cross_country_file).exists():
                self.logger.warning(f"Cross-country line file not found")
                return {}
            
            with open(Path(cross_country_file), "r", encoding="utf-8") as f:
                data = json.load(f)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to load cross-country line data: {e}")
            return {}
    
    def _load_interchange_connections_data(self) -> Dict:
        """Load interchange connections data from JSON file."""
        try:
            try:
                from ....utils.data_path_resolver import get_data_file_path

                interchange_file = get_data_file_path("interchange_connections.json")
            except Exception:
                interchange_file = None

            if not interchange_file or not Path(interchange_file).exists():
                possible_paths = [
                    Path("data/interchange_connections.json"),
                    Path("src/data/interchange_connections.json"),
                    Path(__file__).parent.parent.parent.parent
                    / "data"
                    / "interchange_connections.json",
                ]
                interchange_file = next((p for p in possible_paths if p.exists()), None)

            if not interchange_file or not Path(interchange_file).exists():
                self.logger.warning(f"Interchange connections file not found")
                return {}
            
            with open(Path(interchange_file), "r", encoding="utf-8") as f:
                data = json.load(f)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to load interchange connections data: {e}")
            return {}
    
    def clear_cache(self) -> None:
        """Clear any cached underground station data for all systems."""
        self._london_underground_stations = None
        self._glasgow_subway_stations = None
        self._tyne_wear_metro_stations = None
        self._underground_systems = None
        self.logger.info("Underground data loader cache cleared for all systems")

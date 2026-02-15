"""Pathfinding Algorithm.

This module keeps the public :class:`PathfindingAlgorithm` API stable while moving
implementation details into smaller helper modules to satisfy the project LOC gate.
"""

from __future__ import annotations

import heapq
import logging
from typing import Any, Dict, Optional

from src.core.interfaces.i_data_repository import IDataRepository
from .pathfinding_components.connection_selection import get_best_connection
from .pathfinding_components.station_lookup import find_station_in_graph
from .pathfinding_components.types import PathNode
from .pathfinding_components.underground_bonus import apply_underground_routing_bonus
from .pathfinding_components.walking_penalties import apply_walking_penalties
from .pathfinding_components.weight_calculation import calculate_weight


class PathfindingAlgorithm:
    """Handles pathfinding algorithms for route calculation."""
    
    def __init__(self, data_repository: IDataRepository):
        """
        Initialize the pathfinding algorithm.
        
        Args:
            data_repository: Data repository for accessing railway data
        """
        self.data_repository = data_repository
        self.logger = logging.getLogger(__name__)
    
    def dijkstra_shortest_path(self, start: str, end: str, graph: Dict,
                              weight_func: str = 'time',
                              preferences: Optional[Dict[str, Any]] = None) -> Optional[PathNode]:
        """
        Find shortest path using Dijkstra's algorithm with enhanced pathfinding.
        
        Args:
            start: Starting station name
            end: Destination station name
            graph: Network graph
            weight_func: Weight function ('time', 'distance', 'changes')
            preferences: User preferences for routing
        """
        # Handle London station variants in graph lookup
        graph_start = find_station_in_graph(
            station_name=start, graph=graph, logger=self.logger
        )
        if not graph_start:
            self.logger.warning(f"Start station '{start}' not found in network graph")
            return None
             
        graph_end = find_station_in_graph(station_name=end, graph=graph, logger=self.logger)
        if not graph_end:
            self.logger.warning(f"End station '{end}' not found in network graph")
            return None
            
        # Use the resolved graph station names for the rest of the function
        start = graph_start
        end = graph_end
        
        # Get preferences or use empty dict
        if preferences is None:
            preferences = {}
            
        avoid_walking = preferences.get('avoid_walking', False)
        prefer_direct = preferences.get('prefer_direct', False)
        max_walking_distance_km = preferences.get('max_walking_distance_km', 0.1)
        
        # Check if both stations are on the same line
        common_lines = set()
        for line in self.data_repository.load_railway_lines():
            if start in line.stations and end in line.stations:
                common_lines.add(line.name)
        
        self.logger.debug(f"Starting Dijkstra pathfinding from '{start}' to '{end}' using {weight_func} optimization")
        self.logger.debug(f"Preferences: avoid_walking={avoid_walking}, prefer_direct={prefer_direct}, max_walking_distance_km={max_walking_distance_km}")
        self.logger.debug(f"Common lines between {start} and {end}: {common_lines}")
        
        # Priority queue: (weight, node)
        pq = [PathNode(start, 0.0, 0, 0, [start], [])]
        visited = set()
        distances = {start: 0.0}
        
        # Special priority for stations on main routes
        main_route_stations = {
            "London Waterloo": 2000,
            "London Paddington": 2000,
            "London Kings Cross": 2000,
            "London Euston": 2000,
            "London Liverpool Street": 2000,
            "London Victoria": 1000,
            "London Bridge": 1000
        }
        
        # Determine if we should prioritize a specific London terminal
        southwest_stations = ["Farnborough", "Farnborough North", "Farnborough (Main)", "Basingstoke", "Southampton", "Woking", "Guildford", "Clapham Junction"]
        eastern_stations = ["Colchester", "Chelmsford", "Ipswich", "Norwich"]
        western_stations = ["Reading", "Swindon", "Bristol", "Oxford"]
        
        # Check if we should prioritize a specific terminal based on route
        prioritize_terminal = None
        
        # Regional prioritization for Southwest England
        if "Farnborough" in start or any(station in start for station in southwest_stations):
            prioritize_terminal = "London Waterloo"
            main_route_stations["London Waterloo"] = 3000
            main_route_stations["London Victoria"] = 500
            self.logger.info(f"Prioritizing London Waterloo for Southwest England route")
        elif any(station in start for station in southwest_stations):
            prioritize_terminal = "London Waterloo"
            main_route_stations["London Waterloo"] = 5000
        elif any(station in start for station in eastern_stations):
            prioritize_terminal = "London Liverpool Street"
            main_route_stations["London Liverpool Street"] = 5000
        elif any(station in start for station in western_stations):
            prioritize_terminal = "London Paddington"
            main_route_stations["London Paddington"] = 5000
            
        self.logger.info(f"Prioritizing terminal for route: {prioritize_terminal}")
        
        nodes_explored = 0
        
        while pq:
            current = heapq.heappop(pq)
            nodes_explored += 1
            
            if current.station in visited:
                continue
            
            visited.add(current.station)
            
            if current.station == end:
                self.logger.info(f"Found path from '{start}' to '{end}' after exploring {nodes_explored} nodes")
                self.logger.info(f"Path: {' -> '.join(current.path)}")
                self.logger.info(f"Total distance: {current.distance:.1f}km, time: {current.time}min, changes: {current.changes}")
                return current
            
            # Explore neighbors
            neighbors = graph.get(current.station, {})
            self.logger.debug(f"Exploring {len(neighbors)} neighbors from '{current.station}'")
            
            for next_station, connections in neighbors.items():
                if next_station in visited:
                    continue
                
                # Allow Underground routing for cross-London journeys
                is_london_station = "London" in next_station
                london_terminals = ["London Waterloo", "London Liverpool Street", "London Victoria", "London Paddington",
                                  "London Kings Cross", "London St Pancras", "London Euston", "London Bridge"]
                is_london_terminal = next_station in london_terminals
                
                # Calculate if this is a cross-London journey that might benefit from Underground
                from_is_london = "London" in start
                to_is_london = "London" in end
                
                # Allow Underground routing if:
                # 1. It's a London terminal (always allow)
                # 2. It's a cross-London journey where Underground might be beneficial
                # 3. The journey is longer than 50km (likely cross-London)
                journey_distance = current.distance
                
                # Check for cross-country journeys that should route through London
                is_cross_country = False
                if "Southampton" in start and "Glasgow" in end:
                    is_cross_country = True
                elif "Glasgow" in start and "Southampton" in end:
                    is_cross_country = True
                
                is_cross_london_journey = (not from_is_london and not to_is_london and
                                          (journey_distance > 30 or is_cross_country))
                
                # Skip non-terminal London stations ONLY if it's not a beneficial cross-London journey
                if is_london_station and not is_london_terminal and not is_cross_london_journey:
                    self.logger.debug(f"Skipping non-terminal London station: {next_station} (not cross-London journey)")
                    continue
                elif is_london_station and not is_london_terminal and is_cross_london_journey:
                    self.logger.info(f"Allowing Underground routing for cross-London journey: {next_station}")
                
                # If both start and end are on common lines, ONLY allow connections on those lines
                if common_lines:
                    common_line_connections = [c for c in connections if c['line'] in common_lines]
                    if common_line_connections:
                        connections = common_line_connections
                        self.logger.debug(f"RESTRICTING to common line connections only: {[c['line'] for c in connections]}")
                    else:
                        self.logger.debug(f"Skipping {next_station} - no common line connections available")
                        continue
                
                # Check for South Western Main Line connections from Farnborough
                sw_main_line_connections = []
                if "Farnborough" in start or start == "Clapham Junction":
                    sw_main_line_connections = [c for c in connections
                                              if c.get('line') == "South Western Main Line"
                                              and "Waterloo" in c.get('to_station', "")]
                    if sw_main_line_connections:
                        self.logger.debug(f"Found South Western Main Line connection to Waterloo: {current.station} -> {next_station}")
                        
                direct_connections = [c for c in connections if c.get('is_direct', False)]
                
                # Prioritize connections in this order:
                if sw_main_line_connections:
                    connections_to_check = sw_main_line_connections
                    self.logger.debug(f"Using SW Main Line connection from {current.station} to {next_station}")
                elif direct_connections:
                    connections_to_check = direct_connections
                    self.logger.debug(f"Found direct connection from {current.station} to {next_station}")
                else:
                    connections_to_check = connections
                
                
                # Handle walking connections if avoid_walking is enabled
                if avoid_walking:
                    walking_connections = []
                    non_walking_connections = []
                    
                    for conn in connections_to_check:
                        from_station = current.station
                        to_station = conn['to_station']
                        
                        # Check if these stations are on the same line
                        same_line = False
                        for line in self.data_repository.load_railway_lines():
                            if from_station in line.stations and to_station in line.stations:
                                same_line = True
                                self.logger.info(f"NOT marking as walking - stations are on same line: {from_station} → {to_station} (line: {line.name})")
                                break
                        
                        # Only consider underground connections if not on same line
                        if not same_line:
                            # Check if either station is in London but not a terminal
                            from_is_london = "London" in from_station
                            to_is_london = "London" in to_station
                            london_terminals = ["London Waterloo", "London Liverpool Street", "London Victoria", "London Paddington"]
                            
                            from_is_terminal = from_station in london_terminals
                            to_is_terminal = to_station in london_terminals
                            
                            # Mark as walking if both stations are in London but not both are terminals
                            if from_is_london and to_is_london and not (from_is_terminal and to_is_terminal):
                                walking_connections.append(conn)
                                conn['is_walking_connection'] = True
                                self.logger.info(f"Marking as walking due to both stations being in London: {from_station} → {to_station}")
                                continue
                            elif (from_is_london and not from_is_terminal) or (to_is_london and not to_is_terminal):
                                walking_connections.append(conn)
                                conn['is_walking_connection'] = True
                                self.logger.info(f"Marking as walking due to one non-terminal London station: {from_station} → {to_station}")
                                continue
                            
                        # Check if this is a walking connection between London terminals
                        london_terminals = ["London Waterloo", "London Victoria", "London Paddington",
                                           "London Kings Cross", "London St Pancras", "London Euston",
                                           "London Liverpool Street", "London Bridge", "London Charing Cross"]
                        directly_connected_terminals = [
                            ("London Kings Cross", "London St Pancras"),
                            ("London Waterloo", "London Waterloo East")
                        ]
                        
                        from_is_london_terminal = from_station in london_terminals
                        to_is_london_terminal = to_station in london_terminals
                        
                        # Check if they're London terminals
                        if from_is_london_terminal and to_is_london_terminal:
                            # Check if they're directly connected terminals
                            directly_connected = False
                            for term1, term2 in directly_connected_terminals:
                                if (from_station == term1 and to_station == term2) or (from_station == term2 and to_station == term1):
                                    directly_connected = True
                                    break
                                    
                            if not directly_connected:
                                walking_connections.append(conn)
                                conn['is_walking_connection'] = True
                                self.logger.info(f"Marking as walking due to London terminals: {from_station} → {to_station}")
                                continue
                            
                        # Check if they're on the same line
                        same_line = False
                        for line in self.data_repository.load_railway_lines():
                            if from_station in line.stations and to_station in line.stations:
                                same_line = True
                                break
                        
                        # If stations are on the same line, prefer train connection, not walking
                        if same_line:
                            non_walking_connections.append(conn)
                            self.logger.debug(f"Using train connection for stations on same line: {from_station} → {to_station}")
                            continue
                            
                        # Calculate haversine distance if we have coordinates
                        distance_km = 0
                        if 'distance' in conn:
                            distance_km = conn['distance']
                        
                        # Check explicit walking markers
                        is_walking = (
                            conn.get('line') == 'WALKING' or
                            conn.get('is_walking_connection', False) or
                            ('walking' in conn.get('line', '').lower())
                        )
                        
                        # Apply combined logic to determine if this is a walking connection
                        if is_walking or (not same_line and distance_km > max_walking_distance_km):
                            walking_connections.append(conn)
                            conn['is_walking_connection'] = True
                        else:
                            non_walking_connections.append(conn)
                    
                    # If avoid_walking is true, strictly avoid all walking connections
                    if non_walking_connections:
                        connections_to_check = non_walking_connections
                        self.logger.info(f"Using only {len(non_walking_connections)} non-walking connections from {current.station} to {next_station}")
                        walking_connections = []
                    else:
                        self.logger.warning(f"No non-walking alternatives found from {current.station} to {next_station}")
                        self.logger.warning(f"Network may be disconnected if walking is strictly avoided")
                
                # Find best connection based on weight function with same-line prioritization
                best_connection = get_best_connection(
                    connections=connections_to_check,
                    current=current,
                    start=start,
                    end=end,
                    weight_func=weight_func,
                    data_repository=self.data_repository,
                    logger=self.logger,
                )
                
                if not best_connection:
                    continue
                
                # Calculate new weights using Haversine distance if coordinates available
                new_distance = current.distance + best_connection['distance']
                new_time = current.time + best_connection['time']
                
                # Calculate changes (if switching lines)
                new_changes = current.changes
                if current.lines_used and current.lines_used[-1] != best_connection['line']:
                    # Don't count as a change if it's a direct connection
                    if not best_connection.get('is_direct', False):
                        new_changes += 1
                        new_time += 5  # Add 5 minutes for interchange
                
                new_path = current.path + [next_station]
                new_lines = current.lines_used + [best_connection['line']]
                
                # Choose weight based on function
                weight = calculate_weight(
                    weight_func=weight_func,
                    new_time=new_time,
                    new_distance=new_distance,
                    new_changes=new_changes,
                    best_connection=best_connection,
                )
                
                # Apply Underground routing bonus for cross-London journeys
                weight = apply_underground_routing_bonus(
                    weight=weight,
                    connection=best_connection,
                    current=current,
                    start=start,
                    end=end,
                    logger=self.logger,
                )
                
                # Apply penalties for walking connections
                weight = apply_walking_penalties(
                    weight=weight,
                    connection=best_connection,
                    current_station=current.station,
                    avoid_walking=avoid_walking,
                    max_walking_distance_km=max_walking_distance_km,
                    data_repository=self.data_repository,
                    logger=self.logger,
                )
                
                # Only add to queue if we found a better path
                if next_station not in distances or weight < distances[next_station]:
                    distances[next_station] = weight
                    
                    next_node = PathNode(
                        station=next_station,
                        distance=new_distance,
                        time=new_time,
                        changes=new_changes,
                        path=new_path,
                        lines_used=new_lines
                    )
                    
                    heapq.heappush(pq, next_node)
        
        self.logger.warning(
            "No path found from '%s' to '%s' after exploring %s nodes",
            start,
            end,
            nodes_explored,
        )
        return None
        

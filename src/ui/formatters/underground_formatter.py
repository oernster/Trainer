"""Underground formatter.

UI formatting and display of "black box" Underground routing segments.

Architecture note:
    This module is in the UI layer, so it must not import from the core-domain
    layer under `src/core/**`. Instead, it uses structural typing (Protocols)
    so service-layer adapters can provide compatible objects/DTOs.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol, Sequence

from .underground_resources import (
    SYSTEM_INFO,
    UNDERGROUND_WARNING_TEXT,
    build_underground_css_styles,
)


class RouteSegmentLike(Protocol):
    """Minimal segment shape required by the UI formatter."""

    service_pattern: str
    line_name: str
    from_station: str
    to_station: str
    distance_km: float | None
    journey_time_minutes: int | None


class RouteLike(Protocol):
    """Minimal route shape required by the UI formatter."""

    from_station: str
    to_station: str
    segments: Sequence[RouteSegmentLike]


class UndergroundFormatter:
    """Formats Underground black box routing segments for UI display."""
    
    def __init__(self):
        """Initialize the Underground formatter."""
        self.logger = logging.getLogger(__name__)
        
        # Define colors for Underground display (as hex strings)
        self.underground_color = "#DC241F"  # TfL red
        self.underground_text_color = "#FFFFFF"  # White text
        self.underground_background = "#DC241F32"  # Semi-transparent red
        self.regular_color = "#333333"
        self.regular_background = "#F5F5F5"
        
        # System-specific information
        self.system_info = SYSTEM_INFO
    
    def is_underground_segment(self, segment: RouteSegmentLike) -> bool:
        """
        Check if a route segment is an Underground black box segment for any UK system.
        
        Args:
            segment: The route segment to check
            
        Returns:
            True if this is an Underground segment, False otherwise
        """
        return (segment.service_pattern == "UNDERGROUND" or
                segment.line_name in self.system_info or
                segment.line_name == "UNDERGROUND")
    
    def get_underground_system_info(self, segment: RouteSegmentLike) -> dict[str, str]:
        """
        Get system-specific information for an underground segment.
        
        Args:
            segment: The underground segment
            
        Returns:
            Dictionary with system information
        """
        if not self.is_underground_segment(segment):
            return {}
        
        # Check if line_name matches a known system (exact match first)
        if segment.line_name in self.system_info:
            return self.system_info[segment.line_name]
        
        # Check for system name variations (case-insensitive)
        line_name_lower = segment.line_name.lower().strip()
        
        # Glasgow Subway variations
        if any(term in line_name_lower for term in ["glasgow", "subway"]):
            return self.system_info["Glasgow Subway"]
        
        # Tyne and Wear Metro variations
        if any(term in line_name_lower for term in ["tyne", "wear", "metro", "nexus"]):
            return self.system_info["Tyne and Wear Metro"]
        
        # London Underground variations
        if any(term in line_name_lower for term in ["london", "underground", "tube", "tfl"]):
            return self.system_info["London Underground"]
        
        # If service_pattern is UNDERGROUND but no system match, try to infer from stations
        if segment.service_pattern == "UNDERGROUND":
            # Try to determine system from station names
            from_station = getattr(segment, 'from_station', '').lower()
            to_station = getattr(segment, 'to_station', '').lower()
            
            # Glasgow indicators
            if any(term in from_station or term in to_station for term in ["glasgow", "buchanan", "st enoch"]):
                return self.system_info["Glasgow Subway"]
            
            # Tyne and Wear indicators
            if any(term in from_station or term in to_station for term in ["newcastle", "gateshead", "sunderland", "central station"]):
                return self.system_info["Tyne and Wear Metro"]
        
        # Default to London Underground for backwards compatibility
        return self.system_info["London Underground"]
    
    def format_underground_segment_text(self, segment: RouteSegmentLike) -> str:
        """
        Format the text display for an Underground segment.
        
        Args:
            segment: The Underground segment to format
            
        Returns:
            Formatted text string for display
        """
        if not self.is_underground_segment(segment):
            return f"{segment.from_station} → {segment.to_station}"
        
        # Get system-specific information
        system_info = self.get_underground_system_info(segment)
        emoji = system_info.get("emoji", "🚇")
        system_name = system_info.get("short_name", "Underground")
        time_range = system_info.get("time_range", "10-40min")
        
        # Format as black box Underground segment with system-specific time range
        return f"{emoji} Use {system_name} ({time_range})"
    
    def format_underground_segment_detailed(self, segment: RouteSegmentLike) -> dict[str, str]:
        """
        Format detailed information for an Underground segment.
        
        Args:
            segment: The Underground segment to format
            
        Returns:
            Dictionary with formatted details
        """
        if not self.is_underground_segment(segment):
            return {
                "line": segment.line_name,
                "from": segment.from_station,
                "to": segment.to_station,
                "type": "regular"
            }
        
        # Get system-specific information
        system_info = self.get_underground_system_info(segment)
        system_name = system_info.get("short_name", "Underground")
        emoji = system_info.get("emoji", "🚇")
        time_range = system_info.get("time_range", "10-40min")
        
        return {
            "line": system_name,
            "from": segment.from_station,
            "to": segment.to_station,
            "type": "underground",
            "display_text": f"Use {system_name}",
            "icon": emoji,
            "time": f"({time_range})",
            "distance": f"{segment.distance_km:.1f}km" if segment.distance_km else "~5km"
        }
    
    def get_underground_segment_style(self, segment: RouteSegmentLike) -> dict[str, str]:
        """
        Get styling information for an Underground segment.
        
        Args:
            segment: The segment to style
            
        Returns:
            Dictionary with style properties
        """
        if self.is_underground_segment(segment):
            return {
                "background_color": self.underground_background,
                "border_color": self.underground_color,
                "text_color": self.underground_color,
                "border_width": "2px",
                "border_radius": "6px",
                "padding": "8px",
                "margin": "4px 0",
                "font_weight": "bold",
                "css_class": "underground-segment"
            }
        else:
            return {
                "background_color": self.regular_background,
                "border_color": "#CCCCCC",
                "text_color": self.regular_color,
                "border_width": "1px",
                "border_radius": "4px",
                "padding": "6px",
                "margin": "2px 0",
                "font_weight": "normal",
                "css_class": "regular-segment"
            }
    
    def format_route_with_underground(self, route: RouteLike) -> list[dict[str, Any]]:
        """
        Format a complete route with Underground segments highlighted.
        
        Args:
            route: The route to format
            
        Returns:
            List of formatted segment information
        """
        formatted_segments = []
        
        for i, segment in enumerate(route.segments):
            is_underground = self.is_underground_segment(segment)
            style = self.get_underground_segment_style(segment)
            
            segment_info = {
                "index": i,
                "from_station": segment.from_station,
                "to_station": segment.to_station,
                "line_name": segment.line_name,
                "is_underground": is_underground,
                "journey_time": segment.journey_time_minutes,
                "distance": segment.distance_km,
                "style": style
            }
            
            if is_underground:
                # Get system-specific information
                system_info = self.get_underground_system_info(segment)
                system_name = system_info.get("short_name", "Underground")
                emoji = system_info.get("emoji", "🚇")
                
                segment_info.update({
                    "display_text": f"{emoji} Use {system_name}",
                    "icon": emoji,
                    "description": f"Travel from {segment.from_station} to {segment.to_station} using {system_name}",
                    "instructions": self.format_underground_instructions(segment)
                })
            else:
                segment_info.update({
                    "display_text": f"🚂 {segment.from_station} → {segment.to_station}",
                    "icon": "🚂",
                    "description": f"Travel from {segment.from_station} to {segment.to_station} via {segment.line_name}",
                    "instructions": [f"Board {segment.line_name} service to {segment.to_station}"]
                })
            
            formatted_segments.append(segment_info)
        
        return formatted_segments
    
    def get_underground_route_summary(self, route: RouteLike) -> dict[str, Any]:
        """
        Get a summary of Underground usage in a route.
        
        Args:
            route: The route to analyze
            
        Returns:
            Dictionary with Underground usage summary
        """
        underground_segments = [seg for seg in route.segments if self.is_underground_segment(seg)]
        regular_segments = [seg for seg in route.segments if not self.is_underground_segment(seg)]
        
        underground_time = sum(seg.journey_time_minutes or 0 for seg in underground_segments)
        regular_time = sum(seg.journey_time_minutes or 0 for seg in regular_segments)
        
        underground_distance = sum(seg.distance_km or 0 for seg in underground_segments)
        regular_distance = sum(seg.distance_km or 0 for seg in regular_segments)
        
        total_time = underground_time + regular_time
        total_distance = underground_distance + regular_distance
        
        return {
            "has_underground": len(underground_segments) > 0,
            "underground_segments_count": len(underground_segments),
            "regular_segments_count": len(regular_segments),
            "underground_time_minutes": underground_time,
            "regular_time_minutes": regular_time,
            "underground_distance_km": underground_distance,
            "regular_distance_km": regular_distance,
            "underground_percentage_time": (underground_time / total_time * 100) if total_time > 0 else 0,
            "underground_percentage_distance": (underground_distance / total_distance * 100) if total_distance > 0 else 0,
            "summary_text": self._generate_route_summary_text(underground_segments, regular_segments)
        }
    
    def format_underground_instructions(self, segment: RouteSegmentLike) -> list[str]:
        """
        Generate user-friendly instructions for Underground segments.
        
        Args:
            segment: The Underground segment
            
        Returns:
            List of instruction strings
        """
        if not self.is_underground_segment(segment):
            return [f"Travel from {segment.from_station} to {segment.to_station} via {segment.line_name}"]
        
        # Get system-specific information
        system_info = self.get_underground_system_info(segment)
        system_name = system_info.get("short_name", "Underground")
        time_range = system_info.get("time_range", "10-40min")
        
        instructions = [
            f"Use {system_name} to travel from {segment.from_station} to {segment.to_station}",
            "Follow underground signs and maps",
        ]
        
        # Add system-specific advice
        if "London Underground" in system_name:
            instructions.extend([
                "Check TfL website or app for live service updates",
                "Allow extra time for potential delays"
            ])
        elif "Glasgow Subway" in system_name:
            instructions.extend([
                "Check SPT website or app for service updates",
                "Note: Glasgow Subway is a circular line"
            ])
        elif "Tyne" in system_name:
            instructions.extend([
                "Check Nexus website or app for service updates",
                "Metro connects Newcastle, Gateshead, and Sunderland"
            ])
        else:
            instructions.append("Check local transport website for service updates")
        
        instructions.append(f"Estimated journey time: {time_range}")
        
        return instructions
    
    def get_underground_css_styles(self) -> str:
        """
        Get CSS styles for Underground segment display.
        
        Returns:
            CSS string for styling Underground elements
        """
        return build_underground_css_styles(
            underground_background=self.underground_background,
            underground_color=self.underground_color,
            regular_background=self.regular_background,
            regular_color=self.regular_color,
        )
    
    def format_route_display_text(self, route: RouteLike) -> str:
        """
        Format a route for simple text display.
        
        Args:
            route: The route to format
            
        Returns:
            Formatted text representation of the route
        """
        if not route.segments:
            return f"{route.from_station} → {route.to_station}"
        
        parts = []
        for segment in route.segments:
            if self.is_underground_segment(segment):
                system_info = self.get_underground_system_info(segment)
                emoji = system_info.get("emoji", "🚇")
                system_name = system_info.get("short_name", "Underground")
                parts.append(f"{emoji} {system_name}")
            else:
                parts.append(f"🚂 {segment.line_name}")
        
        return f"{route.from_station} → {route.to_station} via {' → '.join(parts)}"
    
    def get_underground_legend_info(self) -> dict[str, str]:
        """
        Get legend information for Underground display.
        
        Returns:
            Dictionary with legend information
        """
        return {
            "underground_icon": "🚇",
            "underground_text": "UK Underground Systems (black box routing)",
            "underground_description": "Simplified routing through UK underground networks (London Underground, Glasgow Subway, Tyne & Wear Metro)",
            "regular_icon": "🚂",
            "regular_text": "National Rail",
            "regular_description": "Direct National Rail services"
        }
    
    def _generate_route_summary_text(
        self,
        underground_segments: Sequence[RouteSegmentLike],
        regular_segments: Sequence[RouteSegmentLike],
    ) -> str:
        """
        Generate a summary text for the route.
        
        Args:
            underground_segments: List of Underground segments
            regular_segments: List of regular segments
            
        Returns:
            Summary text string
        """
        if not underground_segments:
            return "National Rail only"
        elif not regular_segments:
            # Determine which underground system(s) are used
            systems = set()
            for segment in underground_segments:
                system_info = self.get_underground_system_info(segment)
                systems.add(system_info.get("short_name", "Underground"))
            
            if len(systems) == 1:
                return f"{list(systems)[0]} only"
            else:
                return "Underground systems only"
        else:
            return f"Mixed journey: {len(regular_segments)} National Rail + {len(underground_segments)} Underground segment(s)"
    
    def should_highlight_underground(self, route: RouteLike) -> bool:
        """
        Determine if Underground segments should be highlighted in this route.
        
        Args:
            route: The route to check
            
        Returns:
            True if Underground segments should be highlighted
        """
        return any(self.is_underground_segment(seg) for seg in route.segments)
    
    def get_underground_warning_text(self) -> str:
        """
        Get warning text for Underground routing.
        
        Returns:
            Warning text string
        """
        return UNDERGROUND_WARNING_TEXT

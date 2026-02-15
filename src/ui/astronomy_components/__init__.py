"""
Astronomy Components Package

This package contains all the individual components that make up the astronomy widgets.
Each component is responsible for a specific aspect of the astronomy UI.
"""

# Import all components to make them available when importing from this package
from .astronomy_event_icon import AstronomyEventIcon
from .daily_astronomy_panel import DailyAstronomyPanel
from .astronomy_forecast_panel import AstronomyForecastPanel
from .astronomy_event_details import AstronomyEventDetails
from .astronomy_expandable_panel import AstronomyExpandablePanel
from .astronomy_widget import AstronomyWidget

# Export all components
__all__ = [
    'AstronomyEventIcon',
    'DailyAstronomyPanel',
    'AstronomyForecastPanel',
    'AstronomyEventDetails',
    'AstronomyExpandablePanel',
    'AstronomyWidget'
]
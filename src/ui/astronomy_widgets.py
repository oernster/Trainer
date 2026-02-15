"""
Astronomy Widgets Module

This module serves as the main entry point for all astronomy-related UI components.
It imports and re-exports all the individual components from the astronomy_components package,
maintaining backward compatibility with existing code that imports from this module.
"""

import logging
from typing import Dict, Optional

# Import all components from the astronomy_components package
from .astronomy_components.astronomy_event_icon import AstronomyEventIcon
from .astronomy_components.daily_astronomy_panel import DailyAstronomyPanel
from .astronomy_components.astronomy_forecast_panel import AstronomyForecastPanel
from .astronomy_components.astronomy_event_details import AstronomyEventDetails
from .astronomy_components.astronomy_expandable_panel import AstronomyExpandablePanel
from .astronomy_components.astronomy_widget import AstronomyWidget

# Re-export all components
__all__ = [
    'AstronomyEventIcon',
    'DailyAstronomyPanel',
    'AstronomyForecastPanel',
    'AstronomyEventDetails',
    'AstronomyExpandablePanel',
    'AstronomyWidget'
]

logger = logging.getLogger(__name__)
logger.info("Astronomy widgets module loaded")

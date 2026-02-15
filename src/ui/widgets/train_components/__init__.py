"""
Train widget components package.

This package contains the refactored components of the train item widget,
following the Single Responsibility Principle to improve maintainability.
"""

from .base_component import BaseTrainComponent
from .station_filter_service import StationFilterService
from .train_main_info_section import TrainMainInfoSection
from .train_details_section import TrainDetailsSection
from .calling_points_manager import CallingPointsManager
from .location_info_section import LocationInfoSection

__all__ = [
    'BaseTrainComponent',
    'StationFilterService',
    'TrainMainInfoSection',
    'TrainDetailsSection',
    'CallingPointsManager',
    'LocationInfoSection',
]
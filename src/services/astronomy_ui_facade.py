"""UI-facing DTOs for astronomy.

UI is not allowed to import domain models directly. This module provides a thin
facade for UI code.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class AstronomyEventDTO:
    event_type: str
    title: str
    description: str
    start_time: datetime
    end_time: Optional[datetime] = None
    visibility_info: Optional[str] = None
    image_url: Optional[str] = None
    priority: int = 2


__all__ = ["AstronomyEventDTO"]


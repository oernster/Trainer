"""
Enhanced Moon Phase Service for accurate lunar calculations.
Author: Oliver Ernster

This module provides a hybrid approach combining API-based and local calculations
for maximum accuracy and reliability in moon phase determination.
"""

import logging
import asyncio
import aiohttp
from datetime import date, datetime, timedelta, time, timezone
from typing import Optional, Dict, Any, List, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import json
import math

from ..models.astronomy_data import MoonPhase

logger = logging.getLogger(__name__)


class MoonPhaseSource(Enum):
    """Source of moon phase data."""
    API = "api"
    LOCAL_CALCULATION = "local_calculation"
    CACHED = "cached"


@dataclass
class MoonPhaseResult:
    """Result container for moon phase calculations."""
    phase: MoonPhase
    illumination: float
    source: MoonPhaseSource
    confidence: float  # 0.0 to 1.0
    timestamp: datetime
    next_new_moon: Optional[datetime] = None
    next_full_moon: Optional[datetime] = None


class EnhancedMoonPhaseCalculator:
    """Enhanced local moon phase calculator with multiple reference points."""

    # Mean synodic month length (days). This is the standard value used by many
    # practical phase algorithms and is sufficiently accurate for an 8-phase UI.
    SYNODIC_MONTH_DAYS = 29.530588853

    # A widely-used epoch new moon time (UTC). Source: Meeus / common astronomical
    # references for phase algorithms.
    EPOCH_NEW_MOON_UTC = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)

    # For date-only callers, pick a stable representative time to avoid day-boundary
    # flips (previously a date-only algorithm would frequently drift by ~1 day).
    DEFAULT_DATE_TIME_UTC = time(12, 0)  # 12:00 UTC
    
    def __init__(self):
        """Initialize the enhanced calculator."""
        logger.info("Enhanced Moon Phase Calculator initialized with USNO reference points")
    

    def _to_utc_datetime(self, target: Union[date, datetime]) -> datetime:
        """Normalize a date/datetime input to an aware UTC datetime."""
        if isinstance(target, datetime):
            dt = target
        else:
            dt = datetime.combine(target, self.DEFAULT_DATE_TIME_UTC)

        if dt.tzinfo is None:
            # Treat naive timestamps as UTC to avoid silently using the local OS timezone.
            logger.warning(
                "Naive datetime passed to moon phase calculator; assuming UTC. "
                "Pass a timezone-aware datetime for correct results."
            )
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    def calculate_moon_phase(self, target: Union[date, datetime]) -> Tuple[MoonPhase, float]:
        """Calculate moon phase and illumination for a given moment (UTC-normalized)."""
        dt_utc = self._to_utc_datetime(target)

        seconds_since_epoch = (dt_utc - self.EPOCH_NEW_MOON_UTC).total_seconds()
        cycle_seconds = self.SYNODIC_MONTH_DAYS * 86400.0
        phase_fraction = (seconds_since_epoch / cycle_seconds) % 1.0  # [0, 1)

        # Illumination: 0.0 (new) -> 1.0 (full)
        phase_angle = 2 * math.pi * phase_fraction
        illumination = (1 - math.cos(phase_angle)) / 2

        # Map phase fraction to 8-phase buckets.
        # Boundaries are at 22.5° increments (1/16 of a cycle):
        # new at 0, first quarter at 0.25, full at 0.5, last quarter at 0.75.
        if phase_fraction < 1 / 16 or phase_fraction >= 15 / 16:
            phase = MoonPhase.NEW_MOON
        elif phase_fraction < 3 / 16:
            phase = MoonPhase.WAXING_CRESCENT
        elif phase_fraction < 5 / 16:
            phase = MoonPhase.FIRST_QUARTER
        elif phase_fraction < 7 / 16:
            phase = MoonPhase.WAXING_GIBBOUS
        elif phase_fraction < 9 / 16:
            phase = MoonPhase.FULL_MOON
        elif phase_fraction < 11 / 16:
            phase = MoonPhase.WANING_GIBBOUS
        elif phase_fraction < 13 / 16:
            phase = MoonPhase.LAST_QUARTER
        else:
            phase = MoonPhase.WANING_CRESCENT

        logger.debug(
            "Local calculation (UTC): %s -> %s (phase_fraction=%.4f)",
            dt_utc.isoformat(),
            phase.value,
            phase_fraction,
        )
        return phase, illumination


class MoonPhaseAPI:
    """API service for fetching real-time moon phase data."""
    
    def __init__(self):
        """Initialize the API service."""
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=10.0)
        
    async def _ensure_session(self):
        """Ensure aiohttp session is available."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
    
    async def fetch_from_sunrise_sunset_api(self, target_date: date, lat: float = 51.5074, lon: float = -0.1278) -> Optional[Dict[str, Any]]:
        """Fetch moon phase data from sunrise-sunset.org API (free, no key required)."""
        try:
            await self._ensure_session()
            url = "https://api.sunrise-sunset.org/json"
            params = {
                'lat': lat,
                'lng': lon,
                'date': target_date.isoformat(),
                'formatted': 0
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == 'OK':
                        logger.debug(f"Successfully fetched data from sunrise-sunset API for {target_date}")
                        return data
                        
        except Exception as e:
            logger.warning(f"Failed to fetch from sunrise-sunset API: {e}")
        
        return None
    
    async def fetch_from_timeanddate_api(self, target_date: date) -> Optional[Dict[str, Any]]:
        """Fetch moon phase data from timeanddate.com API (free endpoints)."""
        try:
            await self._ensure_session()
            # TimeAndDate has some free astronomy endpoints
            url = f"https://timeanddate.com/moon/{target_date.isoformat()}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    # This would need HTML parsing - placeholder for now
                    logger.debug(f"TimeAndDate API response received for {target_date}")
                    return {"status": "ok", "date": target_date.isoformat()}
                        
        except Exception as e:
            logger.warning(f"Failed to fetch from TimeAndDate API: {e}")
        
        return None
    
    async def get_moon_phase_from_api(self, target_date: date, lat: float = 51.5074, lon: float = -0.1278) -> Optional[Tuple[MoonPhase, float]]:
        """Attempt to get moon phase from various free APIs."""
        # Try sunrise-sunset API first (most reliable for basic data)
        api_data = await self.fetch_from_sunrise_sunset_api(target_date, lat, lon)
        
        if api_data:
            # For now, we'll use the API to validate our calculations
            # In future versions, we could parse moon phase from specialized endpoints
            logger.info(f"API data received for validation: {target_date}")
            return None  # Placeholder - would implement moon phase parsing
        
        # Try other APIs if needed
        return None
    
    async def cleanup(self):
        """Clean up the session."""
        if self.session and not self.session.closed:
            await self.session.close()


class HybridMoonPhaseService:
    """Hybrid moon phase service combining API and local calculations."""
    
    def __init__(self):
        """Initialize the hybrid service."""
        self.calculator = EnhancedMoonPhaseCalculator()
        self.api = MoonPhaseAPI()
        self.cache: Dict[str, MoonPhaseResult] = {}
        self.cache_duration = timedelta(hours=6)  # Cache for 6 hours
        
    def _get_cache_key(self, target: Union[date, datetime]) -> str:
        """Generate cache key for a target moment.

        - For date-only inputs, cache per-calendar-date.
        - For datetime inputs, cache per-hour (UTC) so the "current" phase can
          move through phase-change boundaries in long-running sessions.
        """
        if isinstance(target, datetime):
            dt = target
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt_utc = dt.astimezone(timezone.utc)
            return f"moon_phase_{dt_utc.strftime('%Y-%m-%dT%H')}Z"

        return f"moon_phase_{target.isoformat()}"
    
    def _is_cache_valid(self, result: MoonPhaseResult) -> bool:
        """Check if cached result is still valid."""
        return (datetime.now() - result.timestamp) < self.cache_duration
    
    async def get_moon_phase(
        self,
        target: Union[date, datetime],
        lat: float = 51.5074,
        lon: float = -0.1278,
    ) -> MoonPhaseResult:
        """Get moon phase using hybrid approach: API first, then local calculation."""
        cache_key = self._get_cache_key(target)
        
        # Check cache first
        if cache_key in self.cache:
            cached_result = self.cache[cache_key]
            if self._is_cache_valid(cached_result):
                logger.debug(f"Returning cached moon phase for {target}")
                return cached_result
        
        # Try API first
        try:
            target_date_for_api = target.date() if isinstance(target, datetime) else target
            api_result = await self.api.get_moon_phase_from_api(target_date_for_api, lat, lon)
            if api_result:
                phase, illumination = api_result
                result = MoonPhaseResult(
                    phase=phase,
                    illumination=illumination,
                    source=MoonPhaseSource.API,
                    confidence=0.95,  # High confidence for API data
                    timestamp=datetime.now()
                )
                
                # Cache the result
                self.cache[cache_key] = result
                logger.info(f"Moon phase from API for {target}: {phase.value}")
                return result
                
        except Exception as e:
            logger.warning(f"API failed for {target}: {e}")
        
        # Fallback to enhanced local calculation
        phase, illumination = self.calculator.calculate_moon_phase(target)
        result = MoonPhaseResult(
            phase=phase,
            illumination=illumination,
            source=MoonPhaseSource.LOCAL_CALCULATION,
            confidence=0.85,  # Good confidence for enhanced local calculation
            timestamp=datetime.now()
        )
        
        # Cache the result
        self.cache[cache_key] = result
        logger.info(f"Moon phase from local calculation for {target}: {phase.value}")
        return result
    
    def get_moon_phase_sync(self, target: Union[date, datetime]) -> MoonPhaseResult:
        """Synchronous version using only local calculation."""
        phase, illumination = self.calculator.calculate_moon_phase(target)
        return MoonPhaseResult(
            phase=phase,
            illumination=illumination,
            source=MoonPhaseSource.LOCAL_CALCULATION,
            confidence=0.85,
            timestamp=datetime.now()
        )
    
    async def cleanup(self):
        """Clean up resources."""
        await self.api.cleanup()
        self.cache.clear()


"""Phase 2 boundary note:

This module intentionally does *not* expose a module-level service instance.

Composition rule:
  - Bootstrap is the only place allowed to assemble the object graph.
  - Callers must receive a [`python.HybridMoonPhaseService`](src/services/moon_phase_service.py:1)
    instance via dependency injection.
"""

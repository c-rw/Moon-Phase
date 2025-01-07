import logging
import azure.functions as func
from datetime import datetime, timedelta
import ephem
import math
import json
from functools import lru_cache
from typing import Dict, Any, Optional, Tuple, List
import pytz
from dataclasses import dataclass

# Configure logging
logger = logging.getLogger(__name__)

# Custom Exceptions
class MoonPhaseError(Exception):
    """Custom exception for moon phase calculation errors"""
    pass

class InvalidInputError(Exception):
    """Custom exception for input validation errors"""
    pass

# Constants
PHASE_NAMES = [
    (0, 6.25, "New Moon"),
    (6.25, 56.25, "Waxing Crescent"),
    (56.25, 97.75, "First Quarter"),
    (97.75, 135.25, "Waxing Gibbous"),
    (135.25, 180.75, "Full Moon"),
    (180.75, 218.25, "Waning Gibbous"),
    (218.25, 258.75, "Last Quarter"),
    (258.75, 360, "Waning Crescent")
]

@dataclass
class LocationData:
    """Data class for location information"""
    lat: float
    lon: float
    date: datetime
    timezone: str

def get_phase_name(phase_percentage: float) -> str:
    """
    Get the name of the moon phase based on percentage.
    
    Args:
        phase_percentage: Moon phase percentage (0-100)
    
    Returns:
        str: Name of the moon phase
    """
    phase_angle = phase_percentage * 360 / 100
    return next(name for start, end, name in PHASE_NAMES 
               if start <= phase_angle < end)

@lru_cache(maxsize=128)
def get_heavenly_body(body_type: str) -> ephem.Body:
    """
    Get cached heavenly body object.
    
    Args:
        body_type: Type of heavenly body ("moon" or "mercury")
    
    Returns:
        ephem.Body: Cached heavenly body object
    """
    if body_type.lower() == "moon":
        return ephem.Moon()
    elif body_type.lower() == "mercury":
        return ephem.Mercury()
    raise ValueError(f"Unknown body type: {body_type}")

def calculate_mercury_retrograde(date: datetime, days_range: int = 180) -> Dict[str, Any]:
    """
    Calculate Mercury's retrograde status and next transition dates.
    Uses ephem to track Mercury's motion and detect direction changes.
    
    Args:
        date: Date to check
        days_range: How many days to look ahead
    
    Returns:
        Dict containing retrograde status and next transition dates
    """
    try:
        mercury = get_heavenly_body("mercury")
        start_date = ephem.Date(date)
        
        # Get initial position
        mercury.compute(start_date)
        initial_long = float(mercury.hlong)
        
        # Check direction of motion
        mercury.compute(start_date + ephem.hour)
        is_retrograde = float(mercury.hlong) - initial_long < 0
        
        next_direct = None
        next_retrograde = None
        current_date = start_date
        last_long = initial_long

        # Look ahead for next transition
        for _ in range(days_range):
            current_date = ephem.Date(current_date + 1)
            mercury.compute(current_date)
            current_long = float(mercury.hlong)
            
            is_moving_backwards = (current_long - last_long) < 0
            
            if is_retrograde and not is_moving_backwards and not next_direct:
                next_direct = ephem.Date(current_date).datetime()
            elif not is_retrograde and is_moving_backwards and not next_retrograde:
                next_retrograde = ephem.Date(current_date).datetime()
                
            if next_direct and next_retrograde:
                break
                
            last_long = current_long

        return {
            "is_retrograde": is_retrograde,
            "next_retrograde_start": next_retrograde.isoformat() if next_retrograde else None,
            "next_retrograde_end": next_direct.isoformat() if next_direct else None
        }
    except Exception as e:
        raise MoonPhaseError(f"Error calculating Mercury retrograde: {str(e)}")

@lru_cache(maxsize=128)
def calculate_moon_phase(date: datetime) -> Dict[str, Any]:
    """
    Calculate moon phase and related data using PyEphem's native capabilities.
    
    Args:
        date: Date to calculate moon phase for
    
    Returns:
        Dict containing moon phase information
    """
    try:
        moon = get_heavenly_body("moon")
        moon.compute(date)
        
        # Get next phase dates using ephem's built-in functions
        next_phases = {
            "next_new_moon": ephem.next_new_moon(date).datetime(),
            "next_first_quarter": ephem.next_first_quarter_moon(date).datetime(),
            "next_full_moon": ephem.next_full_moon(date).datetime(),
            "next_last_quarter": ephem.next_last_quarter_moon(date).datetime()
        }
        
        phase_percentage = moon.phase
        
        return {
            "moon_phase": get_phase_name(phase_percentage),
            "illumination": round(phase_percentage, 1),
            "moon_age": round(moon.age, 2),
            "phase_percentage": round(phase_percentage, 1),
            "is_waxing": phase_percentage < 50,
            "timestamp": date.isoformat(),
            "libration_lat": float(moon.libration_lat),
            "libration_long": float(moon.libration_long),
            "colong": float(moon.colong),
            "subsolar_lat": float(moon.subsolar_lat),
            **{k: v.isoformat() for k, v in next_phases.items()}
        }
    except Exception as e:
        raise MoonPhaseError(f"Error calculating moon phase: {str(e)}")

def calculate_moon_details(location: LocationData) -> Dict[str, Any]:
    """
    Calculate moonrise/set and positional data for a given location and date.
    
    Args:
        location: LocationData object containing location information
    
    Returns:
        Dict containing moon position details
    """
    try:
        observer = ephem.Observer()
        observer.lat = str(location.lat)
        observer.lon = str(location.lon)
        observer.date = location.date
        observer.pressure = 0  # Disable refraction calculation
        observer.horizon = '-0:34'  # Standard atmospheric refraction at horizon
        
        moon = get_heavenly_body("moon")
        moon.compute(observer)
        
        # Calculate rise and set times
        try:
            moonrise = observer.next_rising(moon).datetime()
            moonset = observer.next_setting(moon).datetime()
        except (ephem.CircumpolarError, ephem.NeverUpError) as e:
            logger.warning(f"Special case for moonrise/set: {str(e)}")
            moonrise = None
            moonset = None
        
        # Convert timestamps to requested timezone if specified
        tz = pytz.timezone(location.timezone)
        if moonrise:
            moonrise = moonrise.astimezone(tz)
        if moonset:
            moonset = moonset.astimezone(tz)
        
        return {
            "moonrise": moonrise.isoformat() if moonrise else None,
            "moonset": moonset.isoformat() if moonset else None,
            "altitude": round(math.degrees(float(moon.alt)), 2),
            "azimuth": round(math.degrees(float(moon.az)), 2),
            "distance_km": round(moon.earth_distance * ephem.meters_per_au / 1000, 2),
            "angular_diameter": round(math.degrees(float(moon.size)) * 60, 2),  # Convert to arc-minutes
            "magnitude": round(float(moon.mag), 1)
        }
    except Exception as e:
        raise MoonPhaseError(f"Error calculating moon details: {str(e)}")

def validate_inputs(lat: Optional[str], lon: Optional[str], 
                   date_param: Optional[str], timezone_param: Optional[str]) -> LocationData:
    """
    Validate and parse input parameters.
    
    Args:
        lat: Latitude string
        lon: Longitude string
        date_param: Date string
        timezone_param: Timezone string
    
    Returns:
        LocationData object with validated inputs
    """
    try:
        # Clean inputs
        lat, lon, date_param, timezone_param = map(
            lambda x: x.strip() if x else None, 
            [lat, lon, date_param, timezone_param]
        )
        
        if lat is None or lon is None:
            raise InvalidInputError("Latitude and longitude are required")
        
        # Validate coordinates
        lat_float, lon_float = map(float, [lat, lon])
        
        if not (-90 <= lat_float <= 90):
            raise InvalidInputError("Latitude must be between -90 and 90 degrees")
        if not (-180 <= lon_float <= 180):
            raise InvalidInputError("Longitude must be between -180 and 180 degrees")
        
        # Validate and parse date
        date = datetime.fromisoformat(date_param) if date_param else datetime.utcnow()
        if not (datetime(1900, 1, 1) <= date <= datetime(2100, 1, 1)):
            raise InvalidInputError("Date must be between 1900 and 2100")
        
        # Validate timezone
        timezone = timezone_param or 'UTC'
        if timezone not in pytz.all_timezones:
            raise InvalidInputError("Invalid time zone specified")
        
        return LocationData(
            lat=lat_float,
            lon=lon_float,
            date=pytz.timezone(timezone).localize(date),
            timezone=timezone
        )
    except ValueError as e:
        raise InvalidInputError(f"Invalid input format: {str(e)}")

@lru_cache(maxsize=1000)
def get_cached_response(location: LocationData) -> Dict[str, Any]:
    """
    Cache frequently requested calculations to improve performance.
    
    Args:
        location: LocationData object containing location information
    
    Returns:
        Dict containing combined moon phase and position data
    """
    return {
        **calculate_moon_phase(location.date),
        **calculate_moon_details(location),
        **calculate_mercury_retrograde(location.date)
    }

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main HTTP-triggered function for moon phase and Mercury retrograde API.
    
    Args:
        req: HTTP request object
    
    Returns:
        HTTP response with JSON data
    """
    try:
        logger.info("Moon phase API triggered", extra={
            "params": dict(req.params),
            "url": req.url,
            "method": req.method
        })
        
        # Get and validate inputs
        location = validate_inputs(
            req.params.get("lat"),
            req.params.get("lon"),
            req.params.get("date"),
            req.params.get("timezone")
        )
        
        # Get combined response
        response = get_cached_response(location)
        
        # Add metadata
        response["request_time"] = datetime.utcnow().astimezone(
            pytz.timezone(location.timezone)
        ).isoformat()
        response["api_version"] = "1.2.0"
        
        return func.HttpResponse(
            body=json.dumps(response, default=str),
            mimetype="application/json",
            status_code=200
        )
    except InvalidInputError as e:
        error_response = {"error": "Invalid input", "message": str(e)}
        logger.warning("Invalid input", extra={"error": str(e)})
        return func.HttpResponse(
            body=json.dumps(error_response),
            mimetype="application/json",
            status_code=400
        )
    except MoonPhaseError as e:
        error_response = {"error": "Calculation error", "message": str(e)}
        logger.error("Calculation error", extra={"error": str(e)})
        return func.HttpResponse(
            body=json.dumps(error_response),
            mimetype="application/json",
            status_code=500
        )
    except Exception as e:
        error_response = {
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }
        logger.error("Unexpected error", extra={"error": str(e)}, exc_info=True)
        return func.HttpResponse(
            body=json.dumps(error_response),
            mimetype="application/json",
            status_code=500
        )
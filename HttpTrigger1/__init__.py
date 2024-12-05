import logging
import azure.functions as func
from datetime import datetime, timedelta
import ephem
import math
import json
from functools import lru_cache
from typing import Dict, Any, Optional, Tuple
import pytz

# Configure logging
logger = logging.getLogger(__name__)

class MoonPhaseError(Exception):
    """Custom exception for moon phase calculation errors"""
    pass

class InvalidInputError(Exception):
    """Custom exception for input validation errors"""
    pass

@lru_cache(maxsize=128)
def calculate_moon_phase(date: datetime) -> Dict[str, Any]:
    """
    Calculate moon phase and related data for a given date, including the next new moon,
    first quarter, full moon, and last quarter.
    """
    try:
        reference_new_moon = datetime(2000, 1, 6, 18, 14)  # Reference New Moon date
        synodic_month = 29.530588  # Average length of lunar cycle in days

        # Calculate days since reference new moon
        delta = (date - reference_new_moon).total_seconds() / (24 * 3600)
        phase = (delta % synodic_month) / synodic_month

        # Calculate illumination percentage
        illumination = round((1 - math.cos(2 * math.pi * phase)) * 50, 1)

        # Determine moon phase using precise thresholds
        phase_names = {
            (0.975, 0.025): "New Moon",
            (0.025, 0.235): "Waxing Crescent",
            (0.235, 0.265): "First Quarter",
            (0.265, 0.485): "Waxing Gibbous",
            (0.485, 0.515): "Full Moon",
            (0.515, 0.735): "Waning Gibbous",
            (0.735, 0.765): "Last Quarter",
            (0.765, 0.975): "Waning Crescent"
        }

        if phase > 0.975 or phase < 0.025:
            moon_phase = "New Moon"
        else:
            moon_phase = next(name for (start, end), name in phase_names.items() if start <= phase < end)

        # Calculate moon age
        moon_age = round(delta % synodic_month, 2)

        # Calculate next key phases
        next_phases = {}
        current_lunation = math.floor(delta / synodic_month)
        days_into_cycle = delta % synodic_month
        
        for key_phase, phase_offset in {
            "next_new_moon": 0.0,
            "next_first_quarter": 7.4,  # ~7.4 days after new moon
            "next_full_moon": 14.8,     # ~14.8 days after new moon
            "next_last_quarter": 22.1    # ~22.1 days after new moon
        }.items():
            if days_into_cycle < phase_offset:
                # Next phase is in current cycle
                target_days = (current_lunation * synodic_month) + phase_offset
            else:
                # Next phase is in next cycle
                target_days = ((current_lunation + 1) * synodic_month) + phase_offset
            
            next_phase_date = reference_new_moon + timedelta(days=target_days)
            # Ensure the phase date is in the future
            if next_phase_date <= date:
                next_phase_date += timedelta(days=synodic_month)
            next_phases[key_phase] = next_phase_date.isoformat()

        return {
            "moon_phase": moon_phase,
            "illumination": illumination,
            "moon_age": moon_age,
            "phase_percentage": round(phase * 100, 1),
            "is_waxing": phase < 0.5,
            "timestamp": date.isoformat(),
            **next_phases
        }
    except Exception as e:
        raise MoonPhaseError(f"Error calculating moon phase: {str(e)}")

def calculate_moon_details(lat: float, lon: float, date: datetime) -> Dict[str, Any]:
    """
    Calculate moonrise/set and positional data for a given location and date.
    """
    try:
        observer = ephem.Observer()
        observer.lat = str(lat)
        observer.lon = str(lon)
        observer.date = date
        observer.pressure = 0
        observer.horizon = '-0:34'

        moon = ephem.Moon(observer)
        
        try:
            moonrise = observer.next_rising(moon).datetime()
            moonset = observer.next_setting(moon).datetime()
        except (ephem.CircumpolarError, ephem.NeverUpError) as e:
            moonrise = None
            moonset = None
            logger.warning(f"Special case for moonrise/set: {str(e)}")

        return {
            "moonrise": moonrise.isoformat() if moonrise else None,
            "moonset": moonset.isoformat() if moonset else None,
            "altitude": round(math.degrees(moon.alt), 2),
            "azimuth": round(math.degrees(moon.az), 2),
            "distance_km": round(moon.earth_distance * 149597870.691, 2)
        }
    except Exception as e:
        raise MoonPhaseError(f"Error calculating moon details: {str(e)}")

def validate_inputs(lat: Optional[str], lon: Optional[str], date_param: Optional[str], timezone_param: Optional[str]) -> Tuple[float, float, datetime, str]:
    """
    Validate and parse input parameters.
    """
    try:
        # Input sanitization
        lat = lat.strip() if lat else None
        lon = lon.strip() if lon else None
        date_param = date_param.strip() if date_param else None
        timezone_param = timezone_param.strip() if timezone_param else None

        if lat is None or lon is None:
            raise InvalidInputError("Latitude and longitude are required")
            
        try:
            lat_float = float(lat)
            lon_float = float(lon)
        except ValueError:
            raise InvalidInputError("Latitude and longitude must be valid numbers")
        
        if not (-90 <= lat_float <= 90):
            raise InvalidInputError("Latitude must be between -90 and 90 degrees")
        if not (-180 <= lon_float <= 180):
            raise InvalidInputError("Longitude must be between -180 and 180 degrees")

        if date_param:
            try:
                date = datetime.fromisoformat(date_param)
            except ValueError:
                raise InvalidInputError("Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
            if not (datetime(1900, 1, 1) <= date <= datetime(2100, 1, 1)):
                raise InvalidInputError("Date must be between 1900 and 2100")
        else:
            date = datetime.utcnow()

        timezone = timezone_param or 'UTC'
        if timezone not in pytz.all_timezones:
            raise InvalidInputError("Invalid time zone specified")
        
        return lat_float, lon_float, date, timezone
    except ValueError as e:
        raise InvalidInputError(f"Invalid input format: {str(e)}")

@lru_cache(maxsize=1000)
def get_cached_response(lat: float, lon: float, date: datetime) -> Dict[str, Any]:
    """
    Cache frequently requested calculations to improve performance.
    """
    return {
        **calculate_moon_phase(date),
        **calculate_moon_details(lat, lon, date)
    }

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main HTTP-triggered function for moon phase API.
    """
    try:
        logger.info("Moon phase API triggered", extra={
            "params": dict(req.params),
            "url": req.url,
            "method": req.method
        })

        lat = req.params.get("lat")
        lon = req.params.get("lon")
        date_param = req.params.get("date")
        timezone_param = req.params.get("timezone")

        lat_float, lon_float, date, timezone = validate_inputs(lat, lon, date_param, timezone_param)

        # Use cached response for better performance
        response = get_cached_response(lat_float, lon_float, date)

        # Convert all timestamps to requested timezone
        tz = pytz.timezone(timezone)
        for key in ["timestamp", "next_new_moon", "next_first_quarter", "next_full_moon", 
                   "next_last_quarter", "moonrise", "moonset"]:
            if key in response and response[key]:
                response[key] = datetime.fromisoformat(response[key]).astimezone(tz).isoformat()

        response["request_time"] = datetime.utcnow().astimezone(tz).isoformat()
        response["api_version"] = "1.0.0"

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
        error_response = {"error": "Internal server error", "message": "An unexpected error occurred"}
        logger.error("Unexpected error", extra={"error": str(e)}, exc_info=True)
        return func.HttpResponse(
            body=json.dumps(error_response),
            mimetype="application/json",
            status_code=500
        )
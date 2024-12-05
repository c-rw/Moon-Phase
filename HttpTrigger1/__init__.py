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

        # Determine moon phase using more precise thresholds
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
        for key_phase, phase_offset in {
            "next_new_moon": 0.0,
            "next_first_quarter": 0.25,
            "next_full_moon": 0.5,
            "next_last_quarter": 0.75
        }.items():
            cycles_since_ref = delta / synodic_month
            target_phase_cycles = math.ceil(cycles_since_ref - phase + phase_offset)
            target_phase_days = target_phase_cycles * synodic_month
            next_phases[key_phase] = (reference_new_moon + timedelta(days=target_phase_days)).isoformat()

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

def calculate_eclipse_details(date: datetime) -> Dict[str, Any]:
    """
    Calculate upcoming and past lunar eclipse data relative to a given date.
    """
    try:
        observer = ephem.Observer()
        observer.date = date

        next_eclipse = ephem.next_lunar_eclipse(observer.date)
        next_eclipse_date = next_eclipse[0].datetime() if next_eclipse else None

        prev_eclipse = ephem.previous_lunar_eclipse(observer.date)
        prev_eclipse_date = prev_eclipse[0].datetime() if prev_eclipse else None

        return {
            "next_lunar_eclipse": next_eclipse_date.isoformat() if next_eclipse_date else None,
            "previous_lunar_eclipse": prev_eclipse_date.isoformat() if prev_eclipse_date else None
        }
    except Exception as e:
        raise MoonPhaseError(f"Error calculating lunar eclipses: {str(e)}")

def validate_inputs(lat: Optional[str], lon: Optional[str], date_param: Optional[str], timezone_param: Optional[str]) -> Tuple[float, float, datetime, str]:
    """
    Validate and parse input parameters.
    """
    try:
        if lat is None or lon is None:
            raise InvalidInputError("Latitude and longitude are required")
            
        lat_float = float(lat)
        lon_float = float(lon)
        
        if not (-90 <= lat_float <= 90):
            raise InvalidInputError("Latitude must be between -90 and 90 degrees")
        if not (-180 <= lon_float <= 180):
            raise InvalidInputError("Longitude must be between -180 and 180 degrees")

        if date_param:
            date = datetime.fromisoformat(date_param)
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

        response = calculate_moon_phase(date)
        details = calculate_moon_details(lat_float, lon_float, date)
        response.update(details)

        eclipse_details = calculate_eclipse_details(date)
        response.update(eclipse_details)

        tz = pytz.timezone(timezone)
        for key in ["timestamp", "next_new_moon", "next_first_quarter", "next_full_moon", "next_last_quarter", "moonrise", "moonset", "next_lunar_eclipse", "previous_lunar_eclipse"]:
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
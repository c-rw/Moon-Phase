import logging
import azure.functions as func
from datetime import datetime, timedelta
import ephem
import math
import json

# Helper function to calculate moon phase and related data
def calculate_moon_phase(date):
    reference_new_moon = datetime(2000, 1, 6, 18, 14)  # Reference New Moon date
    synodic_month = 29.530588  # Average length of the lunar cycle in days

    # Days since the reference new moon
    delta = (date - reference_new_moon).total_seconds() / (24 * 3600)
    phase = (delta % synodic_month) / synodic_month

    # Moon illumination percentage
    illumination = round((1 - math.cos(2 * math.pi * phase)) * 50, 1)

    # Determine moon phase
    if phase < 0.03 or phase > 0.97:
        moon_phase = "New Moon"
    elif phase < 0.25:
        moon_phase = "Waxing Crescent"
    elif phase < 0.27:
        moon_phase = "First Quarter"
    elif phase < 0.5:
        moon_phase = "Waxing Gibbous"
    elif phase < 0.53:
        moon_phase = "Full Moon"
    elif phase < 0.75:
        moon_phase = "Waning Gibbous"
    elif phase < 0.77:
        moon_phase = "Last Quarter"
    else:
        moon_phase = "Waning Crescent"

    # Moon age
    moon_age = round(delta % synodic_month, 2)

    # Next full moon
    cycles_since_ref = delta / synodic_month
    next_full_moon_cycles = math.ceil(cycles_since_ref) + 0.5
    next_full_moon_days = next_full_moon_cycles * synodic_month
    next_full_moon_date = reference_new_moon + timedelta(days=next_full_moon_days)

    return {
        "moon_phase": moon_phase,
        "illumination": illumination,
        "moon_age": moon_age,
        "next_full_moon": next_full_moon_date.isoformat()
    }

# Function to calculate moonrise/set and positional data
def calculate_moon_details(lat, lon, date):
    observer = ephem.Observer()
    observer.lat, observer.lon = str(lat), str(lon)
    observer.date = date

    moon = ephem.Moon(observer)
    moonrise = observer.next_rising(moon).datetime()
    moonset = observer.next_setting(moon).datetime()

    return {
        "moonrise": moonrise.isoformat(),
        "moonset": moonset.isoformat(),
        "altitude": round(math.degrees(moon.alt), 2),
        "azimuth": round(math.degrees(moon.az), 2)
    }

# Main HTTP-triggered function
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Moon phase API triggered.")

    # Parse query parameters
    date_param = req.params.get("date")
    lat = req.params.get("lat")
    lon = req.params.get("lon")

    try:
        # Use current UTC date if no date is provided
        date = datetime.fromisoformat(date_param) if date_param else datetime.utcnow()

        # Basic moon phase calculation
        response = calculate_moon_phase(date)

        # Add moonrise/set and positional data if lat/lon provided
        if lat and lon:
            details = calculate_moon_details(float(lat), float(lon), date)
            response.update(details)

        # Return a properly serialized JSON response
        return func.HttpResponse(
            body=json.dumps(response),  # Serialize dictionary to JSON
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return func.HttpResponse(
            body=json.dumps({"error": "Invalid request. Please provide valid inputs."}),
            mimetype="application/json",
            status_code=400
        )

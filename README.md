# Azure Function: Moon Phase API

## Overview

This Azure Function is an HTTP-triggered API that calculates moon phase data and related positional details based on user-provided inputs. It includes the moon's phase, illumination percentage, moonrise/set times, and positional data (altitude, azimuth, and distance from Earth). The function uses precise astronomical calculations and validates user inputs for accuracy.

## Features

- **Moon Phase Calculation**: Determines the moon's phase (e.g., New Moon, Full Moon) based on the date.
- **Illumination Percentage**: Calculates how much of the moon's surface is illuminated.
- **Moonrise and Moonset**: Provides the times for moonrise and moonset at the specified location.
- **Positional Data**: Includes altitude, azimuth, and distance of the moon.
- **Error Handling**: Custom exceptions and detailed error responses for invalid inputs or calculation errors.

## Usage

### Request Parameters

The API accepts the following query parameters:

- `lat` (required): Latitude of the location (-90 to 90 degrees).
- `lon` (required): Longitude of the location (-180 to 180 degrees).
- `date` (optional): ISO 8601 formatted date (e.g., `2024-11-30`). Defaults to the current UTC date if not provided.

### Example Request

```http
GET /api/moonphase?lat=40.7128&lon=-74.0060&date=2024-11-30
```

### Response Format

The response is a JSON object containing the following fields:

- **Moon Phase Data**:
  - `moon_phase`: Name of the current moon phase.
  - `illumination`: Illumination percentage.
  - `moon_age`: Age of the moon in days.
  - `next_full_moon`: Date of the next full moon.
  - `phase_percentage`: Percentage of the current lunar phase.
  - `is_waxing`: Boolean indicating whether the moon is waxing.

- **Positional Data**:
  - `moonrise`: ISO 8601 formatted time for moonrise.
  - `moonset`: ISO 8601 formatted time for moonset.
  - `altitude`: Moon's altitude in degrees.
  - `azimuth`: Moon's azimuth in degrees.
  - `distance_km`: Distance of the moon from Earth in kilometers.

- **Metadata**:
  - `request_time`: Time the request was processed.
  - `api_version`: Current API version (`1.0.0`).

### Example Response

```json
{
  "moon_phase": "Waxing Crescent",
  "illumination": 23.5,
  "moon_age": 3.4,
  "next_full_moon": "2024-12-14T12:15:00",
  "phase_percentage": 11.7,
  "is_waxing": true,
  "moonrise": "2024-11-30T06:12:00",
  "moonset": "2024-11-30T17:45:00",
  "altitude": 45.6,
  "azimuth": 120.3,
  "distance_km": 384400.12,
  "request_time": "2024-11-30T15:00:00",
  "api_version": "1.0.0"
}
```

## Implementation Details

- **Language**: Python
- **Libraries**:
  - `azure.functions`: For Azure Function integrations.
  - `ephem`: For precise astronomical calculations.
  - `datetime`: For date and time manipulations.
  - `math`: For mathematical operations.
  - `functools.lru_cache`: To optimize repetitive calculations.
- **Error Handling**:
  - `MoonPhaseError`: Raised for calculation errors.
  - `InvalidInputError`: Raised for invalid inputs.
  - General exception handling for unexpected errors.

## Deployment Instructions

1. **Prerequisites**:
   - Azure subscription.
   - Python runtime installed locally.

2. **Setup**:
   - Deploy the function to an Azure Function App.
   - Configure the required runtime (`Python 3.10`).

3. **Testing**:
   - Use tools like Postman or Curl to test the endpoint.
   - Ensure valid latitude, longitude, and date values are provided.

4. **Monitoring**:
   - Use Azure Application Insights for real-time logging and diagnostics.

## Future Enhancements

- Add support for additional astronomical calculations.
- Enhance error messaging for special edge cases (e.g., moonrise/set unavailability).
- Optimize API response time with caching.

This function is reliable for providing lunar data and can be easily integrated into applications requiring moon phase information.

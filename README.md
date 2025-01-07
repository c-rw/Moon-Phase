# Azure Function: Moon Phase and Mercury Retrograde API

## Overview

This Azure Function is an HTTP-triggered API that calculates the moon's phase, positional data, and Mercury's retrograde status. It uses precise astronomical calculations with timezone localization and optimized caching for performance.

---

## Features

- **Moon Phase Information**: Calculates the moon's phase, illumination percentage, and age.
- **Mercury Retrograde**: Detects Mercury's retrograde status and provides transition dates.
- **Moonrise and Moonset**: Provides moonrise and moonset times for a specified location.
- **Moon Positional Data**: Computes altitude, azimuth, and distance from Earth.
- **Timezone Localization**: All timestamps are adjusted to the provided timezone.
- **Optimized Performance**: Frequently requested calculations are cached for efficiency.

---

## API Usage

### Request Parameters

| Parameter       | Required | Description                                 |
|------------------|----------|---------------------------------------------|
| `lat`           | Yes      | Latitude (-90 to 90).                       |
| `lon`           | Yes      | Longitude (-180 to 180).                    |
| `date`          | No       | ISO 8601 date (defaults to current UTC).    |
| `timezone`      | No       | Timezone (defaults to `UTC`).               |

---

### Example Request

```http
GET /api/moonphase?lat=40.7128&lon=-74.0060&date=2025-01-01T00:00:00Z&timezone=America/New_York
```

---

### Response Format

The API returns a JSON object with the following fields:

- **Moon Phase**:
  - `moon_phase`, `illumination`, `moon_age`, `is_waxing`.
  - Dates for upcoming lunar phases: `next_new_moon`, `next_full_moon`, etc.

- **Mercury Retrograde**:
  - `is_retrograde`: Current retrograde status.
  - Transition dates: `next_retrograde_start`, `next_retrograde_end`.

- **Moon Positional Data**:
  - `moonrise`, `moonset`, `altitude`, `azimuth`, `distance_km`.

- **Metadata**:
  - `request_time`: API request timestamp.
  - `api_version`: Current version of the API.

---

### Example Response

```json
{
  "moon_phase": "Waxing Crescent",
  "illumination": 45.3,
  "moon_age": 7.5,
  "next_full_moon": "2025-01-25T03:41:00Z",
  "is_retrograde": false,
  "next_retrograde_start": "2025-03-12T14:00:00Z",
  "moonrise": "2025-01-01T06:12:00-05:00",
  "moonset": "2025-01-01T18:45:00-05:00",
  "altitude": 45.6,
  "azimuth": 120.3,
  "distance_km": 384400.12,
  "request_time": "2025-01-01T00:00:00-05:00",
  "api_version": "1.2.0"
}
```

---

## Deployment

1. **Setup Azure Function App**:
   - Deploy using Azure CLI or portal.
   - Install dependencies:
     ```bash
     pip install -r requirements.txt
     ```

2. **Test API**:
   - Validate using Curl, Postman, or browser.

3. **Monitor**:
   - Use Azure Application Insights for logs and diagnostics.

---

## Future Enhancements

- Support additional planetary retrograde calculations.
- Handle edge cases like polar moonrise/set behavior.

--- 

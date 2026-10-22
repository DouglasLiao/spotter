"""
Centralized domain constants for the routing application.
"""

# Unit conversions
METERS_TO_MILES = 0.000621371
EARTH_RADIUS_MILES = 3958.8

# Batching and default sampling configuration
DEFAULT_SAMPLE_INTERVAL_MILES = 25.0
WEATHER_BATCH_CHUNK_SIZE = 40

# Fast offline fallback for major freight hubs to guarantee resilience
FALLBACK_HUBS = {
    "chicago": {"name": "Chicago, IL, USA", "lat": 41.8781, "lon": -87.6298},
    "denver": {"name": "Denver, CO, USA", "lat": 39.7392, "lon": -104.9903},
    "atlanta": {"name": "Atlanta, GA, USA", "lat": 33.7490, "lon": -84.3880},
    "dallas": {"name": "Dallas, TX, USA", "lat": 32.7767, "lon": -96.7970},
    "seattle": {"name": "Seattle, WA, USA", "lat": 47.6062, "lon": -122.3321},
    "los angeles": {"name": "Los Angeles, CA, USA", "lat": 34.0522, "lon": -118.2437},
    "new york": {"name": "New York, NY, USA", "lat": 40.7128, "lon": -74.0060},
    "miami": {"name": "Miami, FL, USA", "lat": 25.7617, "lon": -80.1918},
    "kansas city": {"name": "Kansas City, MO, USA", "lat": 39.0997, "lon": -94.5786},
    "houston": {"name": "Houston, TX, USA", "lat": 29.7604, "lon": -95.3698},
}

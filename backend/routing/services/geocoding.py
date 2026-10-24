import logging
import math
import re
import urllib.parse

import requests
from django.conf import settings

from routing.constants import FALLBACK_HUBS

logger = logging.getLogger(__name__)


def geocode(query: str) -> dict:
    """
    Geocodes a location query into (lat, lon) coordinates and formatted name.
    Supports:
      1. Coordinate pairs: '41.8781, -87.6298'
      2. City/Address search via Photon API (OpenStreetMap)
      3. Fallback to Nominatim if Photon is unavailable
      4. Fallback to standard logistics hubs
    """
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("Location query cannot be empty.")

    # 1. Check if user passed coordinates directly: "lat, lon"
    coord_match = re.match(
        r"^([-+]?\d{1,2}(?:\.\d+)?)\s*,\s*([-+]?\d{1,3}(?:\.\d+)?)$", clean_query
    )
    if coord_match:
        lat = float(coord_match.group(1))
        lon = float(coord_match.group(2))
        logger.debug(
            "Parsed direct coordinates for '%s': (%f, %f)", clean_query, lat, lon
        )
        return {
            "name": f"{lat:.4f}, {lon:.4f}",
            "lat": lat,
            "lon": lon,
            "formatted_address": f"{lat:.4f}, {lon:.4f}",
        }

    logger.debug("Geocoding query via external services: '%s'", clean_query)

    # 2. Query Photon API
    photon_url = settings.PHOTON_GEOCODE_URL
    user_agent = settings.USER_AGENT
    timeout = settings.EXTERNAL_API_TIMEOUT
    encoded_q = urllib.parse.quote(clean_query)
    url = f"{photon_url}?q={encoded_q}&limit=1"

    try:
        response = requests.get(
            url, headers={"User-Agent": user_agent}, timeout=timeout
        )
        if response.status_code == 200:
            data = response.json()
            features = data.get("features", [])
            if features:
                feature = features[0]
                coords = feature["geometry"]["coordinates"]  # [lon, lat]
                props = feature.get("properties", {})

                parts = [props.get("name"), props.get("state"), props.get("country")]
                formatted = ", ".join(p for p in parts if p) or clean_query
                logger.info(
                    "Photon resolved '%s' -> (%.4f, %.4f)",
                    clean_query,
                    coords[1],
                    coords[0],
                )
                return {
                    "name": props.get("name", clean_query),
                    "lat": coords[1],
                    "lon": coords[0],
                    "formatted_address": formatted,
                }
    except Exception as e:
        logger.warning("Photon geocoding error for '%s': %s", clean_query, e)

    # 3. Fallback to Nominatim
    try:
        nom_url = f"https://nominatim.openstreetmap.org/search?q={encoded_q}&format=json&limit=1"
        response = requests.get(
            nom_url, headers={"User-Agent": user_agent}, timeout=timeout
        )
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, list):
                item = data[0]
                lat = float(item["lat"])
                lon = float(item["lon"])
                logger.info(
                    "Nominatim resolved '%s' -> (%.4f, %.4f)", clean_query, lat, lon
                )
                return {
                    "name": item.get("display_name", clean_query).split(",")[0],
                    "lat": lat,
                    "lon": lon,
                    "formatted_address": item.get("display_name", clean_query),
                }
    except Exception as e:
        logger.warning("Nominatim geocoding error for '%s': %s", clean_query, e)

    # 4. Fallback for logistics hubs if external APIs timed out
    query_lower = clean_query.lower()
    for key, hub in FALLBACK_HUBS.items():
        if key in query_lower:
            logger.info(
                "Resolved '%s' via internal freight hub cache -> %s",
                clean_query,
                hub["name"],
            )
            return {
                "name": hub["name"],
                "lat": hub["lat"],
                "lon": hub["lon"],
                "formatted_address": hub["name"],
            }

    logger.error("Failed to geocode location: '%s'", clean_query)
    raise ValueError(
        f"Unable to geocode location: '{clean_query}'. Please provide a valid city, address, or coordinates."
    )


def search_cities(query: str) -> list[dict]:
    """Return distinct city choices; an unavailable provider must not look like no matches."""
    response = requests.get(
        settings.PHOTON_GEOCODE_URL,
        params={"q": query, "limit": 6, "layer": "city", "lang": "en"},
        headers={"User-Agent": settings.USER_AGENT},
        timeout=settings.EXTERNAL_API_TIMEOUT,
    )
    response.raise_for_status()
    features = response.json()["features"]
    if not isinstance(features, list):
        raise ValueError("Invalid city search response")
    results = []
    seen = set()
    for feature in features:
        try:
            props = feature["properties"]
            lon, lat = map(float, feature["geometry"]["coordinates"])
            if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
                continue
            name = props.get("name") or props.get("city")
            if not name:
                continue
            label = ", ".join(dict.fromkeys(str(part) for part in (name, props.get("state"), props.get("country")) if part))
            key = (label, lat, lon)
            if key not in seen:
                results.append({"name": name, "formatted_address": label, "lat": lat, "lon": lon})
                seen.add(key)
        except (KeyError, TypeError, ValueError):
            continue
    return results[:6]

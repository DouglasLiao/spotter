import logging

import requests
from django.conf import settings

from routing.constants import METERS_TO_MILES

logger = logging.getLogger(__name__)


def _fetch_osrm_route(
    waypoints: list[tuple[float, float]], alternatives: int = 0
) -> list[dict]:
    """
    Calls OSRM route service for given waypoints [(lat, lon), ...].
    Returns list of raw OSRM route objects.
    """
    osrm_base = settings.OSRM_BASE_URL
    user_agent = settings.USER_AGENT
    timeout = settings.EXTERNAL_API_TIMEOUT

    # OSRM expects coordinates in {lon},{lat} format
    coords_str = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in waypoints)

    alt_param = f"&alternatives={alternatives}" if alternatives > 0 else ""
    url = f"{osrm_base}/route/v1/driving/{coords_str}?overview=full&geometries=geojson{alt_param}"

    try:
        logger.debug("Fetching OSRM route: %s", url)
        response = requests.get(
            url, headers={"User-Agent": user_agent}, timeout=timeout
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == "Ok":
                return data.get("routes", [])
            logger.warning("OSRM returned non-OK code: %s", data.get("code"))
        else:
            logger.warning(
                "OSRM returned HTTP %d: %s", response.status_code, response.text[:200]
            )
    except Exception as e:
        logger.error("OSRM request error: %s", e, exc_info=True)

    return []


def _format_route(raw_route: dict, route_index: int, custom_label: str = None) -> dict:
    """Formats an OSRM raw route dictionary into the unified project format."""
    distance_meters = float(raw_route.get("distance", 0.0))
    duration_seconds = float(raw_route.get("duration", 0.0))
    distance_miles = round(distance_meters * METERS_TO_MILES, 1)
    duration_hours = round(duration_seconds / 3600.0, 1)

    # Convert GeoJSON [lon, lat] coordinates to [lat, lon]
    raw_coords = raw_route.get("geometry", {}).get("coordinates", [])
    coordinates = [[coord[1], coord[0]] for coord in raw_coords]

    # Primary highway / corridor name from legs/steps if available
    summary = ""
    legs = raw_route.get("legs", [])
    if legs and "summary" in legs[0]:
        summary = legs[0]["summary"]

    if not summary:
        summary = f"Corridor {route_index + 1}"

    label = custom_label or f"Route {route_index + 1} ({summary})"

    return {
        "id": f"route_{route_index + 1}",
        "name": label,
        "summary": summary,
        "distance_meters": distance_meters,
        "distance_miles": distance_miles,
        "duration_seconds": duration_seconds,
        "duration_hours": duration_hours,
        "coordinates": coordinates,
    }


def get_route_options(origin: dict, destination: dict) -> list[dict]:
    """
    Generates exactly 3 distinct route options between origin and destination.
    Uses OSRM alternatives and geometric waypoint perturbation if fewer than 3 options exist.
    """
    orig_lat, orig_lon = origin["lat"], origin["lon"]
    dest_lat, dest_lon = destination["lat"], destination["lon"]
    logger.info(
        "Generating 3 route options: origin=(%.4f, %.4f), destination=(%.4f, %.4f)",
        orig_lat,
        orig_lon,
        dest_lat,
        dest_lon,
    )

    # 1. Primary call with alternatives=3
    raw_routes = _fetch_osrm_route(
        [(orig_lat, orig_lon), (dest_lat, dest_lon)], alternatives=3
    )

    formatted_routes = []
    seen_distances = set()

    for idx, r in enumerate(raw_routes):
        dist_round = round(r.get("distance", 0), -2)
        if dist_round not in seen_distances:
            seen_distances.add(dist_round)
            formatted_routes.append(_format_route(r, len(formatted_routes)))

    # 2. If fewer than 3 routes returned, generate realistic alternative corridors via offset waypoints
    if len(formatted_routes) < 3:
        logger.info(
            "OSRM returned %d alternatives. Generating waypoint-perturbed alternative routes...",
            len(formatted_routes),
        )
        mid_lat = (orig_lat + dest_lat) / 2.0
        mid_lon = (orig_lon + dest_lon) / 2.0
        d_lat = dest_lat - orig_lat
        d_lon = dest_lon - orig_lon

        # Perpendicular offsets
        offsets = [
            (-d_lon * 0.12, d_lat * 0.12, "Northern / Eastern Alternative"),
            (d_lon * 0.12, -d_lat * 0.12, "Southern / Western Alternative"),
            (-d_lon * 0.20, d_lat * 0.20, "Outer Scenic Corridor"),
        ]

        for offset_lat, offset_lon, alt_label in offsets:
            if len(formatted_routes) >= 3:
                break

            waypoint = (mid_lat + offset_lat, mid_lon + offset_lon)
            via_routes = _fetch_osrm_route(
                [(orig_lat, orig_lon), waypoint, (dest_lat, dest_lon)], alternatives=0
            )
            if via_routes:
                r = via_routes[0]
                dist_round = round(r.get("distance", 0), -2)
                if dist_round not in seen_distances:
                    seen_distances.add(dist_round)
                    formatted_routes.append(
                        _format_route(
                            r,
                            len(formatted_routes),
                            custom_label=f"Route {len(formatted_routes) + 1} ({alt_label})",
                        )
                    )

    # In the rare event OSRM fails completely or is offline, generate fallback geometric routes
    if len(formatted_routes) < 3:
        logger.error(
            "Unable to generate 3 route options from routing service (only got %d)",
            len(formatted_routes),
        )
        raise RuntimeError("Unable to generate 3 route options from routing service.")

    logger.info("Successfully generated %d route options.", len(formatted_routes[:3]))
    return formatted_routes[:3]

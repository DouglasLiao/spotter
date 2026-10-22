import logging
import math
from datetime import datetime, timedelta

from routing.constants import EARTH_RADIUS_MILES

logger = logging.getLogger(__name__)


def haversine_distance_miles(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Calculates geodesic distance between two points in miles using Haversine formula."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_MILES * c


def interpolate_coordinate(
    lat1: float, lon1: float, lat2: float, lon2: float, fraction: float
) -> tuple[float, float]:
    """Linearly interpolates between two coordinates by a given fraction (0.0 to 1.0)."""
    lat = lat1 + (lat2 - lat1) * fraction
    lon = lon1 + (lon2 - lon1) * fraction
    return lat, lon


def sample_route_checkpoints(
    coordinates: list[list[float]],
    total_distance_miles: float,
    total_duration_seconds: float,
    departure_time: datetime,
    interval_miles: float = 25.0,
) -> list[dict]:
    """
    Samples checkpoints along a route's polyline at fixed intervals (10, 25, or 50 miles).
    Always includes the start (mile 0) and the destination.
    Computes the truck's estimated arrival time (ETA) at each checkpoint.

    coordinates: List of [lat, lon]
    interval_miles: Interval distance in miles (e.g. 10.0, 25.0, 50.0)
    """
    if not coordinates:
        return []

    if len(coordinates) == 1 or total_distance_miles <= 0:
        return [
            {
                "index": 0,
                "lat": coordinates[0][0],
                "lon": coordinates[0][1],
                "distance_from_start_miles": 0.0,
                "segment_miles": 0.0,
                "eta": departure_time,
                "eta_iso": departure_time.isoformat(),
            }
        ]

    # Calculate cumulative distance along polyline vertices
    vertex_distances = [0.0]
    accumulated = 0.0
    for i in range(1, len(coordinates)):
        d = haversine_distance_miles(
            coordinates[i - 1][0],
            coordinates[i - 1][1],
            coordinates[i][0],
            coordinates[i][1],
        )
        accumulated += d
        vertex_distances.append(accumulated)

    route_geo_dist = (
        vertex_distances[-1] if vertex_distances[-1] > 0 else total_distance_miles
    )
    # Scale factor between polyline haversine distance and route provider distance
    scale_factor = total_distance_miles / route_geo_dist if route_geo_dist > 0 else 1.0

    # Determine sample distances: 0, interval, 2*interval, ..., end
    target_distances = []
    current_dist = 0.0
    while current_dist < total_distance_miles - (interval_miles * 0.3):
        target_distances.append(current_dist)
        current_dist += interval_miles
    # Always include the destination
    target_distances.append(total_distance_miles)

    checkpoints = []
    v_idx = 0
    num_vertices = len(coordinates)

    for idx, target_dist in enumerate(target_distances):
        # Convert target distance back to polyline coordinate space
        target_geo_dist = target_dist / scale_factor

        # Find the segment [v_idx, v_idx + 1] containing target_geo_dist
        while (
            v_idx < num_vertices - 2 and vertex_distances[v_idx + 1] < target_geo_dist
        ):
            v_idx += 1

        seg_start_dist = vertex_distances[v_idx]
        seg_end_dist = vertex_distances[v_idx + 1]
        seg_len = seg_end_dist - seg_start_dist

        if seg_len > 0:
            fraction = max(0.0, min(1.0, (target_geo_dist - seg_start_dist) / seg_len))
        else:
            fraction = 0.0

        p1 = coordinates[v_idx]
        p2 = coordinates[v_idx + 1]
        lat, lon = interpolate_coordinate(p1[0], p1[1], p2[0], p2[1], fraction)

        # Calculate ETA based on proportional travel time
        time_ratio = (
            (target_dist / total_distance_miles) if total_distance_miles > 0 else 0.0
        )
        elapsed_seconds = total_duration_seconds * time_ratio
        eta = departure_time + timedelta(seconds=elapsed_seconds)

        # Segment miles represented by this checkpoint (distance from previous checkpoint)
        if idx == 0:
            segment_miles = 0.0
        else:
            segment_miles = round(target_dist - target_distances[idx - 1], 2)

        checkpoints.append(
            {
                "index": idx,
                "lat": round(lat, 5),
                "lon": round(lon, 5),
                "distance_from_start_miles": round(target_dist, 1),
                "segment_miles": segment_miles,
                "eta": eta,
                "eta_iso": eta.isoformat(),
            }
        )

    logger.debug(
        "Sampled %d checkpoints (interval=%.1f miles, total=%.1f miles)",
        len(checkpoints),
        interval_miles,
        total_distance_miles,
    )
    return checkpoints

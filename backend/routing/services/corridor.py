"""A bounded regular weather grid covering every returned route's corridor."""
import math

from routing.constants import EARTH_RADIUS_MILES

CORRIDOR_HALF_WIDTH_MILES = 15.0
GRID_SPACING_MILES = 25.0
MAX_GRID_POINTS = 240


def build_corridor_grid(routes: list[dict], departure_time) -> dict:
    coordinates = [point for route in routes for point in route["coordinates"]]
    if not coordinates:
        return {"points": [], "half_width_miles": CORRIDOR_HALF_WIDTH_MILES, "grid_spacing_miles": GRID_SPACING_MILES}
    reference_lat = sum(point[0] for point in coordinates) / len(coordinates)
    reference_lon = coordinates[0][1]
    miles_per_degree = EARTH_RADIUS_MILES * math.pi / 180
    longitude_scale = miles_per_degree * max(0.05, math.cos(math.radians(reference_lat)))

    def project(point):
        return ((point[1] - reference_lon) * longitude_scale, (point[0] - reference_lat) * miles_per_degree)

    segments = []
    for route in routes:
        projected = [project(point) for point in route["coordinates"]]
        segments.extend(zip(projected, projected[1:] or projected))

    spacing = GRID_SPACING_MILES
    while True:
        cells = set()
        for (ax, ay), (bx, by) in segments:
            dx, dy = bx - ax, by - ay
            length_squared = dx * dx + dy * dy
            width = CORRIDOR_HALF_WIDTH_MILES
            for ix in range(math.ceil((min(ax, bx) - width) / spacing), math.floor((max(ax, bx) + width) / spacing) + 1):
                for iy in range(math.ceil((min(ay, by) - width) / spacing), math.floor((max(ay, by) + width) / spacing) + 1):
                    x, y = ix * spacing, iy * spacing
                    t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / length_squared)) if length_squared else 0
                    if math.hypot(x - ax - t * dx, y - ay - t * dy) <= width:
                        cells.add((ix, iy))
        if len(cells) <= MAX_GRID_POINTS:
            break
        spacing *= 1.5

    points = [
        {"lat": round(reference_lat + iy * spacing / miles_per_degree, 5),
         "lon": round(reference_lon + ix * spacing / longitude_scale, 5),
         "eta": departure_time}
        for ix, iy in sorted(cells)
    ]
    return {"points": points, "half_width_miles": CORRIDOR_HALF_WIDTH_MILES,
            "grid_spacing_miles": round(spacing, 2), "max_points": MAX_GRID_POINTS}

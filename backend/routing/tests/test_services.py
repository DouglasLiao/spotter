from datetime import UTC, datetime

from django.test import TestCase

from routing.services.geocoding import geocode
from routing.services.sampler import (
    haversine_distance_miles,
    interpolate_coordinate,
    sample_route_checkpoints,
)


class SamplerServiceTests(TestCase):
    def test_haversine_distance(self):
        # Distance between Chicago (41.8781, -87.6298) and Denver (39.7392, -104.9903) is ~919 air miles
        dist = haversine_distance_miles(41.8781, -87.6298, 39.7392, -104.9903)
        self.assertAlmostEqual(dist, 919.0, delta=15.0)

    def test_interpolate_coordinate(self):
        lat, lon = interpolate_coordinate(0.0, 0.0, 10.0, 20.0, 0.5)
        self.assertEqual(lat, 5.0)
        self.assertEqual(lon, 10.0)

    def test_sample_route_checkpoints(self):
        # Straight line north for 100 miles (approx 1.45 degrees latitude)
        coords = [
            [40.0, -90.0],
            [40.725, -90.0],
            [41.45, -90.0],
        ]
        total_dist = 100.0
        total_dur = 7200.0  # 2 hours
        dep_time = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)

        checkpoints = sample_route_checkpoints(
            coords, total_dist, total_dur, dep_time, interval_miles=25.0
        )

        # Expect checkpoints at 0, 25, 50, 75, 100 miles -> 5 checkpoints
        self.assertEqual(len(checkpoints), 5)
        self.assertEqual(checkpoints[0]["distance_from_start_miles"], 0.0)
        self.assertEqual(checkpoints[0]["eta"], dep_time)
        self.assertEqual(checkpoints[-1]["distance_from_start_miles"], 100.0)
        # Final ETA should be departure + 7200 seconds (14:00 UTC)
        self.assertEqual(checkpoints[-1]["eta"].hour, 14)


class GeocodingServiceTests(TestCase):
    def test_direct_coordinates_parsing(self):
        res = geocode("41.8781, -87.6298")
        self.assertAlmostEqual(res["lat"], 41.8781)
        self.assertAlmostEqual(res["lon"], -87.6298)

    def test_empty_query_raises_error(self):
        with self.assertRaises(ValueError):
            geocode("   ")

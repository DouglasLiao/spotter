from datetime import UTC, datetime

from django.test import SimpleTestCase

from routing.services.corridor import MAX_GRID_POINTS, build_corridor_grid
from routing.services.sampler import haversine_distance_miles


class CorridorTests(SimpleTestCase):
    def test_grid_samples_off_route_and_covers_alternative_corridors(self):
        routes = [
            {'coordinates': [[40, -90], [40, -85]]},
            {'coordinates': [[42, -90], [42, -85]]},
        ]
        result = build_corridor_grid(routes, datetime.now(UTC))
        points = result['points']
        self.assertTrue(any(abs(point['lat'] - 40) < 0.2 for point in points))
        self.assertTrue(any(abs(point['lat'] - 42) < 0.2 for point in points))
        self.assertTrue(any(0.02 < abs(point['lat'] - 40) < 0.2 for point in points))
        self.assertTrue(all(-90.3 < point['lon'] < -84.7 for point in points))
        self.assertEqual(len({(point['lat'], point['lon']) for point in points}), len(points))

    def test_grid_is_bounded_for_long_routes(self):
        routes = [{'coordinates': [[30 + i * 2, -125], [30 + i * 2, -70]]} for i in range(3)]
        result = build_corridor_grid(routes, datetime.now(UTC))
        self.assertGreater(len(result['points']), 0)
        self.assertLessEqual(len(result['points']), MAX_GRID_POINTS)
        self.assertGreater(result['grid_spacing_miles'], 25)

    def test_sampling_keeps_short_last_interval_and_start(self):
        from routing.services.sampler import sample_route_checkpoints
        points = sample_route_checkpoints([[40, -90], [41.5, -90]], 105, 7200, datetime.now(UTC), 25)
        self.assertEqual([point['distance_from_start_miles'] for point in points], [0, 25, 50, 75, 100, 105])
        self.assertAlmostEqual(sum(point['segment_miles'] for point in points), 105)
        self.assertLess(haversine_distance_miles(points[-1]['lat'], points[-1]['lon'], 41.5, -90), 0.001)

from unittest.mock import patch

from django.test import SimpleTestCase

from routing.services.route_provider import get_route_options

ORIGIN = {'lat': 40, 'lon': -90}
DESTINATION = {'lat': 41, 'lon': -89}


def raw_route(offset=0, distance=160934):
    return {'distance': distance, 'duration': 7200, 'geometry': {'coordinates': [
        [-90, 40], [-89.5, 40.5 + offset], [-89, 41],
    ]}}


class RouteProviderTests(SimpleTestCase):
    @patch('routing.services.route_provider._fetch_osrm_route')
    def test_distinct_geometries_with_same_length_are_kept(self, fetch):
        fetch.return_value = [raw_route(0), raw_route(0.2), raw_route(-0.2)]
        routes = get_route_options(ORIGIN, DESTINATION)
        self.assertEqual(len(routes), 3)
        self.assertEqual(fetch.call_count, 1)

    @patch('routing.services.route_provider._fetch_osrm_route')
    def test_duplicate_geometry_is_not_presented_as_three_routes(self, fetch):
        fetch.return_value = [raw_route()]
        self.assertEqual(len(get_route_options(ORIGIN, DESTINATION)), 1)
        self.assertEqual(fetch.call_count, 4)

    @patch('routing.services.route_provider._fetch_osrm_route', return_value=[])
    def test_no_route_raises_instead_of_fabricating_a_path(self, _fetch):
        with self.assertRaises(RuntimeError):
            get_route_options(ORIGIN, DESTINATION)

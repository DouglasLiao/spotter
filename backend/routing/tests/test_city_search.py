from unittest.mock import patch

import requests
from rest_framework.test import APISimpleTestCase

from routing.services.geocoding import search_cities
from routing.tests.test_weather_client import response


class CitySearchTests(APISimpleTestCase):
    @patch('routing.services.geocoding.requests.get')
    def test_city_labels_coordinates_and_deduplication(self, get):
        city = {'properties': {'name': 'Springfield', 'state': 'Illinois', 'country': 'United States'},
                'geometry': {'coordinates': [-89.65, 39.78]}}
        get.return_value = response({'features': [city, city, {}, {'geometry': {'coordinates': [999, 100]}}]})
        result = self.client.get('/api/cities/', {'q': 'Spring'})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data['results'], [{'name': 'Springfield', 'formatted_address': 'Springfield, Illinois, United States', 'lat': 39.78, 'lon': -89.65}])
        self.assertEqual(get.call_args.kwargs['params']['layer'], 'city')

    @patch('routing.services.geocoding.requests.get')
    def test_empty_search_no_matches_and_outage_are_distinct(self, get):
        self.assertEqual(self.client.get('/api/cities/?q=ab').data, {'results': []})
        get.assert_not_called()
        get.return_value = response({'features': []})
        self.assertEqual(search_cities('Nowhere'), [])
        get.side_effect = requests.Timeout()
        self.assertEqual(self.client.get('/api/cities/?q=Chicago').status_code, 503)

    @patch('routing.views.get_route_options', return_value=[])
    @patch('routing.views.geocode')
    def test_selected_coordinates_bypass_ambiguous_geocoding(self, geocode, routes):
        origin = {'lat': 39.78, 'lon': -89.65, 'formatted_address': 'Springfield, Illinois, United States'}
        destination = {'lat': 40, 'lon': -90, 'formatted_address': 'Destination'}
        self.client.post('/api/routes/plan/', {'origin': origin['formatted_address'], 'destination': 'Destination',
                         'origin_location': origin, 'destination_location': destination, 'load_weight': 42000}, format='json')
        geocode.assert_not_called()
        routes.assert_called_once_with(origin, destination)

    def test_invalid_selected_coordinates_are_rejected(self):
        result = self.client.post('/api/routes/plan/', {'origin': 'A', 'destination': 'B', 'load_weight': 1,
                                  'origin_location': {'lat': 91, 'lon': 0, 'formatted_address': 'A'}}, format='json')
        self.assertEqual(result.status_code, 400)

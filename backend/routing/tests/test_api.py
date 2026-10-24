from rest_framework import status
from rest_framework.test import APITestCase


class RoutePlanAPITests(APITestCase):
    def test_missing_fields_returns_400(self):
        response = self.client.post("/api/routes/plan/", {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("origin", response.data)
        self.assertIn("destination", response.data)
        self.assertIn("load_weight", response.data)

    def test_same_origin_and_destination_returns_400(self):
        payload = {
            "origin": "Chicago",
            "destination": "Chicago",
            "load_weight": 35000,
        }
        response = self.client.post("/api/routes/plan/", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("destination", response.data)

    def test_invalid_interval_returns_400(self):
        payload = {
            "origin": "Chicago, IL",
            "destination": "Denver, CO",
            "load_weight": 35000,
            "sample_interval_miles": 15,  # Only 10, 25, 50 allowed
        }
        response = self.client.post("/api/routes/plan/", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("sample_interval_miles", response.data)


class RoutePlanningIntegrationTests(APITestCase):
    """Exercise real services and serialization with only external HTTP mocked."""
    def plan(self, weather_mode='ok', route_count=3, duration_hours=None):
        from unittest.mock import patch
        import requests
        from routing.tests.test_weather_client import forecast, response
        from routing.tests.test_route_provider import raw_route

        def fetch(url, **kwargs):
            if '/route/v1/' in url:
                routes = [raw_route(i * 0.2) for i in range(route_count)]
                if duration_hours is not None:
                    for route in routes:
                        route['duration'] = duration_hours * 3600
                return response({'code': 'Ok', 'routes': routes})
            if weather_mode == 'offline':
                raise requests.Timeout('Weather offline')
            result = []
            for index, _lat in enumerate(kwargs['params']['latitude'].split(',')):
                data = forecast()
                data['hourly']['wind_speed_10m'] = [44.5] * 96
                if weather_mode == 'partial' and index == 1:
                    data['hourly']['rain'] = [None] * 96
                result.append(data)
            return response(result)

        with patch('requests.get', side_effect=fetch):
            return self.client.post('/api/routes/plan/', {
                'origin': '40,-90', 'destination': '41,-89',
                'departure_time': '2026-10-24T12:30:00Z',
                'load_weight': 42000, 'sample_interval_miles': 25,
            }, format='json')

    def test_successful_pipeline_returns_eta_risk_and_aligned_corridor(self):
        result = self.plan()
        self.assertEqual(result.status_code, 200)
        data = result.json()
        self.assertEqual(len(data['routes']), 3)
        self.assertIsNotNone(data['recommended_route_id'])
        self.assertEqual(sum(route['is_recommended'] for route in data['routes']), 1)
        for route in data['routes']:
            self.assertTrue(route['risk_summary']['weather_complete'])
            self.assertEqual(route['risk_summary']['average_risk_score'], 4)
            for checkpoint in route['checkpoints']:
                self.assertEqual(checkpoint['risk']['overall_risk_label'], 'Severe')
                self.assertTrue(checkpoint['risk']['load_penalty_applied'])
                self.assertTrue(checkpoint['weather']['forecast_time'].endswith('+00:00'))
        point = data['corridor']['points'][0]
        self.assertEqual(point['hourly_forecast'][0]['time'], '2026-10-24T12:30:00+00:00')
        self.assertEqual(point['hourly_forecast'][48]['time'], '2026-10-26T12:30:00+00:00')
        self.assertEqual(point['hourly_forecast'][0]['risk_label'], 'Severe')

    def test_weather_outage_returns_unknown_and_no_recommendation(self):
        result = self.plan('offline')
        self.assertEqual(result.status_code, 200)
        data = result.json()
        self.assertIsNone(data['recommended_route_id'])
        self.assertTrue(data['warnings'])
        for route in data['routes']:
            self.assertFalse(route['is_recommended'])
            self.assertIsNone(route['risk_summary']['average_risk_score'])
            self.assertEqual(route['risk_summary']['unknown_miles'], route['distance_miles'])
            self.assertTrue(all(cp['risk']['overall_risk_label'] == 'Unknown' for cp in route['checkpoints']))
        self.assertFalse(data['corridor']['points'][0]['hourly_forecast'][0]['available'])

    def test_partial_weather_excludes_affected_routes(self):
        result = self.plan('partial')
        self.assertEqual(result.status_code, 200)
        data = result.json()
        affected = [route for route in data['routes'] if not route['risk_summary']['weather_complete']]
        self.assertTrue(affected)
        self.assertTrue(all(not route['is_recommended'] for route in affected))

    def test_one_real_route_is_returned_with_warning(self):
        result = self.plan(route_count=1)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(result.data['routes']), 1)
        self.assertTrue(any('Only 1' in warning for warning in result.data['warnings']))

    def test_routing_failure_returns_502(self):
        result = self.plan(route_count=0)
        self.assertEqual(result.status_code, 502)


    def test_long_route_response_extends_corridor_through_arrival(self):
        result = self.plan(duration_hours=60.5)
        self.assertEqual(result.status_code, 200)
        hourly = result.data['corridor']['points'][0]['hourly_forecast']
        self.assertEqual(len(hourly), 62)
        self.assertTrue(hourly[60]['available'])
        self.assertEqual(hourly[61]['time'], '2026-10-27T01:30:00+00:00')

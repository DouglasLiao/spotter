import copy
from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase

from routing.services.weather_client import get_weather_for_checkpoints

START = datetime(2026, 10, 24, 0, tzinfo=UTC)


def forecast(hours=96):
    return {"hourly": {
        "time": [(START + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(hours)],
        "wind_speed_10m": [float(i) for i in range(hours)],
        "rain": [0.05] * hours,
        "showers": [0.0] * hours,
        "snowfall": [0.0] * hours,
    }}


def response(data):
    result = Mock()
    result.status_code = 200
    result.raise_for_status.return_value = None
    result.json.return_value = data
    return result


class WeatherClientTests(SimpleTestCase):
    def point(self, hour=15):
        return {"lat": 41.0, "lon": -87.0, "eta": START + timedelta(hours=hour)}

    @patch('routing.services.weather_client.requests.get')
    def test_departure_window_and_eta_are_distinct_utc_hours(self, get):
        get.return_value = response(forecast())
        departure = (START + timedelta(hours=12, minutes=30)).astimezone(timezone(timedelta(hours=-3)))
        point = get_weather_for_checkpoints([self.point(15)], departure)[0]
        self.assertEqual(point['weather']['wind_mph'], 15)
        self.assertEqual(point['weather']['forecast_time'], '2026-10-24T15:00:00+00:00')
        window = point['hourly_forecast']
        self.assertEqual(len(window), 49)
        self.assertEqual(window[0]['time'], '2026-10-24T12:30:00+00:00')
        self.assertEqual(window[0]['wind_mph'], 12)
        self.assertEqual(window[48]['wind_mph'], 60)
        self.assertEqual(window[48]['time'], '2026-10-26T12:30:00+00:00')
        self.assertEqual(get.call_args.kwargs['params']['hourly'], 'wind_speed_10m,rain,showers,snowfall')
        self.assertEqual(get.call_args.kwargs['params']['precipitation_unit'], 'inch')

    @patch('routing.services.weather_client.requests.get')
    def test_timeout_preserves_all_49_hours_as_unavailable(self, get):
        get.side_effect = requests.Timeout('offline')
        point = get_weather_for_checkpoints([self.point()])[0]
        self.assertFalse(point['weather']['available'])
        self.assertIsNone(point['weather']['wind_mph'])
        self.assertEqual(len(point['hourly_forecast']), 49)
        self.assertTrue(all(not item['available'] for item in point['hourly_forecast']))

    @patch('routing.services.weather_client.requests.get')
    def test_http_failure_is_unavailable(self, get):
        get.return_value.raise_for_status.side_effect = requests.HTTPError('429')
        self.assertFalse(get_weather_for_checkpoints([self.point()])[0]['weather']['available'])

    @patch('routing.services.weather_client.requests.get')
    def test_null_missing_invalid_values_and_malformed_series_are_unknown(self, get):
        for value in (None, -1, float('nan'), float('inf'), '0', True):
            with self.subTest(value=value):
                data = forecast()
                data['hourly']['rain'][15] = value
                get.return_value = response(data)
                self.assertFalse(get_weather_for_checkpoints([self.point()])[0]['weather']['available'])
        for series in ([], None, 'invalid'):
            data = forecast()
            data['hourly']['rain'] = series
            get.return_value = response(data)
            self.assertFalse(get_weather_for_checkpoints([self.point()])[0]['weather']['available'])

    @patch('routing.services.weather_client.requests.get')
    def test_outside_horizon_never_uses_nearest_day(self, get):
        get.return_value = response(forecast(24))
        point = get_weather_for_checkpoints([self.point(30)], START)[0]
        self.assertFalse(point['weather']['available'])
        self.assertTrue(point['hourly_forecast'][23]['available'])
        self.assertFalse(point['hourly_forecast'][24]['available'])

    @patch('routing.services.weather_client.requests.get')
    def test_deduplicates_coordinates_but_preserves_individual_etas(self, get):
        get.return_value = response(forecast())
        points = get_weather_for_checkpoints([self.point(12), self.point(15)], START)
        self.assertEqual(get.call_count, 1)
        self.assertEqual(get.call_args.kwargs['params']['latitude'], '41.0')
        self.assertEqual([cp['weather']['wind_mph'] for cp in points], [12, 15])

    @patch('routing.services.weather_client.requests.get')
    def test_short_location_response_does_not_shift_weather_to_another_point(self, get):
        points = [self.point(), self.point() | {'lat': 42.0}]
        get.return_value = response([forecast()])
        self.assertTrue(all(not cp['weather']['available'] for cp in get_weather_for_checkpoints(points)))

    @patch('routing.services.weather_client.requests.get')
    def test_multiple_locations_and_chunking(self, get):
        def fetch(_url, **kwargs):
            return response([copy.deepcopy(forecast()) for _ in kwargs['params']['latitude'].split(',')])
        get.side_effect = fetch
        points = [self.point() | {'lat': 40 + index / 100} for index in range(41)]
        result = get_weather_for_checkpoints(points, START)
        self.assertEqual(get.call_count, 2)
        self.assertTrue(all(cp['weather']['available'] for cp in result))

    @patch('routing.services.weather_client.requests.get')
    def test_measurements_are_not_rounded_before_risk_classification(self, get):
        data = forecast()
        data['hourly']['rain'][15] = 0.099
        get.return_value = response(data)
        self.assertEqual(get_weather_for_checkpoints([self.point()])[0]['weather']['rain_in_hr'], 0.099)

    @patch('routing.services.weather_client.requests.get')
    def test_rain_includes_showers_without_counting_snow_as_rain(self, get):
        data = forecast()
        data['hourly']['rain'][15] = 0.05
        data['hourly']['showers'][15] = 0.25
        data['hourly']['snowfall'][15] = 2.0
        get.return_value = response(data)
        weather = get_weather_for_checkpoints([self.point()])[0]['weather']
        self.assertAlmostEqual(weather['rain_in_hr'], 0.3)
        self.assertEqual(weather['snow_in_hr'], 2.0)

    @patch('routing.services.weather_client.requests.get')
    def test_long_trip_extends_window_without_inventing_missing_forecasts(self, get):
        get.return_value = response(forecast(72))
        point = get_weather_for_checkpoints([self.point(60)], START, forecast_hours=80)[0]
        self.assertEqual(len(point['hourly_forecast']), 81)
        self.assertEqual(point['weather']['wind_mph'], 60)
        self.assertTrue(point['hourly_forecast'][60]['available'])
        self.assertFalse(point['hourly_forecast'][72]['available'])
        self.assertIsNone(point['hourly_forecast'][80]['wind_mph'])
        bounded = get_weather_for_checkpoints([self.point(500)], START, forecast_hours=500)[0]
        self.assertEqual(len(bounded['hourly_forecast']), 385)
        self.assertFalse(bounded['weather']['available'])

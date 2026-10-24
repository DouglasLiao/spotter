from django.test import TestCase

from routing.services.risk_engine import (
    RiskLevel,
    apply_load_rules,
    calculate_route_risk_metrics,
    classify_rain,
    classify_snow,
    classify_wind,
    evaluate_checkpoint_risk,
)


class RiskEngineClassificationTests(TestCase):
    def test_wind_classification(self):
        self.assertEqual(classify_wind(10.0), RiskLevel.LOW)
        self.assertEqual(classify_wind(24.9), RiskLevel.LOW)
        self.assertEqual(classify_wind(25.0), RiskLevel.MODERATE)
        self.assertEqual(classify_wind(34.0), RiskLevel.MODERATE)
        self.assertEqual(classify_wind(35.0), RiskLevel.HIGH)
        self.assertEqual(classify_wind(44.0), RiskLevel.HIGH)
        self.assertEqual(classify_wind(45.0), RiskLevel.SEVERE)
        self.assertEqual(classify_wind(54.0), RiskLevel.SEVERE)
        self.assertEqual(classify_wind(55.0), RiskLevel.NO_TRAVEL)
        self.assertEqual(classify_wind(70.0), RiskLevel.NO_TRAVEL)

    def test_rain_classification(self):
        self.assertEqual(classify_rain(0.05), RiskLevel.LOW)
        self.assertEqual(classify_rain(0.10), RiskLevel.MODERATE)
        self.assertEqual(classify_rain(0.25), RiskLevel.HIGH)
        self.assertEqual(classify_rain(0.50), RiskLevel.SEVERE)
        self.assertEqual(classify_rain(1.00), RiskLevel.SEVERE)
        self.assertEqual(classify_rain(1.01), RiskLevel.NO_TRAVEL)

    def test_snow_classification(self):
        self.assertEqual(classify_snow(0.2), RiskLevel.LOW)
        self.assertEqual(classify_snow(0.5), RiskLevel.MODERATE)
        self.assertEqual(classify_snow(1.0), RiskLevel.HIGH)
        self.assertEqual(classify_snow(2.0), RiskLevel.SEVERE)
        self.assertEqual(classify_snow(3.0), RiskLevel.SEVERE)
        self.assertEqual(classify_snow(3.1), RiskLevel.NO_TRAVEL)


class LoadRulesTests(TestCase):
    def test_wind_55_plus_is_no_travel_for_any_weight(self):
        # Rule: >= 55 mph -> No Travel for any load
        risk, _penalty, _ = apply_load_rules(wind_mph=55.0, load_weight_lbs=10000.0)
        self.assertEqual(risk, RiskLevel.NO_TRAVEL)

        risk, _penalty, _ = apply_load_rules(wind_mph=60.0, load_weight_lbs=50000.0)
        self.assertEqual(risk, RiskLevel.NO_TRAVEL)

    def test_wind_45_to_54_with_heavy_load_rule(self):
        # Rule: 45–54 mph + >30,000 lb -> No Travel
        # Standard load (<= 30k) -> Severe (no escalation)
        risk, penalty, _ = apply_load_rules(wind_mph=50.0, load_weight_lbs=25000.0)
        self.assertEqual(risk, RiskLevel.SEVERE)
        self.assertFalse(penalty)

        # Overweight load (> 30k) -> Escalated to No Travel
        risk, penalty, reason = apply_load_rules(wind_mph=50.0, load_weight_lbs=35000.0)
        self.assertEqual(risk, RiskLevel.NO_TRAVEL)
        self.assertTrue(penalty)
        self.assertIn("escalated to No Travel", reason)

    def test_wind_35_to_44_with_heavy_load_rule(self):
        # Rule: 35–44 mph + >40,000 lb -> Severe
        # Standard load (<= 40k) -> High (no escalation)
        risk, penalty, _ = apply_load_rules(wind_mph=40.0, load_weight_lbs=38000.0)
        self.assertEqual(risk, RiskLevel.HIGH)
        self.assertFalse(penalty)

        # Overweight load (> 40k) -> Escalated to Severe
        risk, penalty, reason = apply_load_rules(wind_mph=40.0, load_weight_lbs=45000.0)
        self.assertEqual(risk, RiskLevel.SEVERE)
        self.assertTrue(penalty)
        self.assertIn("escalated to Severe", reason)


class CheckpointAndRouteRiskTests(TestCase):
    def test_checkpoint_overall_risk_takes_maximum(self):
        # Wind: Moderate (28 mph), Rain: Low (0.05), Snow: Severe (2.5 in/hr)
        weather = {"wind_mph": 28.0, "rain_in_hr": 0.05, "snow_in_hr": 2.5}
        result = evaluate_checkpoint_risk(weather, load_weight_lbs=20000.0)

        self.assertEqual(result["overall_risk_level"], RiskLevel.SEVERE.value)
        self.assertEqual(result["overall_risk_label"], "Severe")
        self.assertEqual(result["snow_risk_label"], "Severe")
        self.assertEqual(result["wind_risk_label"], "Moderate")

    def test_route_risk_metrics_aggregation(self):
        # 3 checkpoints of 10 miles each: Low, High, Severe
        checkpoints = [
            {
                "segment_miles": 10.0,
                "risk": {"overall_risk_level": RiskLevel.LOW.value},
            },
            {
                "segment_miles": 10.0,
                "risk": {"overall_risk_level": RiskLevel.HIGH.value},
            },
            {
                "segment_miles": 10.0,
                "risk": {"overall_risk_level": RiskLevel.SEVERE.value},
            },
        ]
        metrics = calculate_route_risk_metrics(checkpoints)

        # Total miles = 30. Low: 10 mi, High: 10 mi, Severe: 10 mi
        self.assertEqual(metrics["low_miles"], 10.0)
        self.assertEqual(metrics["high_miles"], 10.0)
        self.assertEqual(metrics["severe_miles"], 10.0)
        # Weighted average: (10*1 + 10*3 + 10*4) / 30 = 80/30 = 2.67
        self.assertEqual(metrics["average_risk_score"], 2.67)
        self.assertEqual(metrics["max_risk_level"], "Severe")


class MissingAndDecimalWeatherTests(TestCase):
    def test_decimal_wind_and_exact_load_boundaries(self):
        for wind, load, expected in [
            (44.5, 40000, RiskLevel.HIGH), (44.5, 40000.1, RiskLevel.SEVERE),
            (44.99, 45000, RiskLevel.SEVERE), (54.5, 30000, RiskLevel.SEVERE),
            (54.5, 30000.1, RiskLevel.NO_TRAVEL), (54.99, 31000, RiskLevel.NO_TRAVEL),
            (55, 0, RiskLevel.NO_TRAVEL),
        ]:
            with self.subTest(wind=wind, load=load):
                self.assertEqual(apply_load_rules(wind, load)[0], expected)

    def test_unknown_weather_is_not_low(self):
        for weather in ({}, {'wind_mph': None}, {'wind_mph': 0, 'rain_in_hr': 0, 'snow_in_hr': None}):
            self.assertEqual(evaluate_checkpoint_risk(weather, 0)['overall_risk_label'], 'Unknown')

    def test_partial_metrics_cannot_claim_known_average_or_peak(self):
        checkpoints = [
            {'segment_miles': 25, 'risk': {'overall_risk_level': None}},
            {'segment_miles': 25, 'risk': {'overall_risk_level': 1}},
        ]
        metrics = calculate_route_risk_metrics(checkpoints)
        self.assertFalse(metrics['weather_complete'])
        self.assertEqual(metrics['unknown_miles'], 25)
        self.assertEqual(metrics['low_miles'], 25)
        self.assertIsNone(metrics['average_risk_score'])
        self.assertEqual(metrics['max_risk_level'], 'Unknown')

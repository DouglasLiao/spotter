from django.test import TestCase

from routing.services.recommender import recommend_best_route


class RecommenderServiceTests(TestCase):
    def test_prefers_fewest_severe_miles(self):
        # Route 1: 0 severe miles, but longer duration
        r1 = {
            "id": "route_1",
            "name": "Route 1",
            "duration_hours": 10.0,
            "duration_seconds": 36000,
            "risk_summary": {
                "severe_miles": 0.0,
                "high_miles": 50.0,
                "average_risk_score": 2.5,
            },
        }
        # Route 2: 5 severe miles, but shorter duration
        r2 = {
            "id": "route_2",
            "name": "Route 2",
            "duration_hours": 8.0,
            "duration_seconds": 28800,
            "risk_summary": {
                "severe_miles": 5.0,
                "high_miles": 10.0,
                "average_risk_score": 2.0,
            },
        }

        best, routes = recommend_best_route([r1, r2])
        self.assertEqual(best["id"], "route_1")
        self.assertTrue(r1["is_recommended"])
        self.assertFalse(r2["is_recommended"])

    def test_prefers_fewest_high_miles_when_severe_tied(self):
        # Both routes have 0 severe miles
        r1 = {
            "id": "route_1",
            "name": "Route 1",
            "duration_hours": 12.0,
            "duration_seconds": 43200,
            "risk_summary": {
                "severe_miles": 0.0,
                "high_miles": 10.0,  # Winner: fewer high miles
                "average_risk_score": 1.8,
            },
        }
        r2 = {
            "id": "route_2",
            "name": "Route 2",
            "duration_hours": 10.0,
            "duration_seconds": 36000,
            "risk_summary": {
                "severe_miles": 0.0,
                "high_miles": 30.0,
                "average_risk_score": 1.5,
            },
        }

        best, _ = recommend_best_route([r1, r2])
        self.assertEqual(best["id"], "route_1")

    def test_prefers_lowest_average_risk_when_severe_and_high_tied(self):
        # Severe=0, High=10 on both
        r1 = {
            "id": "route_1",
            "name": "Route 1",
            "duration_hours": 10.0,
            "duration_seconds": 36000,
            "risk_summary": {
                "severe_miles": 0.0,
                "high_miles": 10.0,
                "average_risk_score": 1.3,  # Winner: lower avg risk
            },
        }
        r2 = {
            "id": "route_2",
            "name": "Route 2",
            "duration_hours": 9.0,
            "duration_seconds": 32400,
            "risk_summary": {
                "severe_miles": 0.0,
                "high_miles": 10.0,
                "average_risk_score": 1.8,
            },
        }

        best, _ = recommend_best_route([r1, r2])
        self.assertEqual(best["id"], "route_1")

    def test_prefers_shortest_time_when_all_risk_tied(self):
        # Severe, High, Avg risk all identical
        r1 = {
            "id": "route_1",
            "name": "Route 1",
            "duration_hours": 9.5,
            "duration_seconds": 34200,
            "risk_summary": {
                "severe_miles": 0.0,
                "high_miles": 10.0,
                "average_risk_score": 1.5,
            },
        }
        r2 = {
            "id": "route_2",
            "name": "Route 2",
            "duration_hours": 8.0,
            "duration_seconds": 28800,  # Winner: faster
            "risk_summary": {
                "severe_miles": 0.0,
                "high_miles": 10.0,
                "average_risk_score": 1.5,
            },
        }

        best, _ = recommend_best_route([r1, r2])
        self.assertEqual(best["id"], "route_2")


class IncompleteWeatherRecommendationTests(TestCase):
    def test_unknown_routes_are_excluded_and_all_unknown_yields_no_recommendation(self):
        unknown = {'id': 'unknown', 'risk_summary': {'weather_complete': False, 'average_risk_score': None}}
        known = {'id': 'known', 'name': 'Known route', 'duration_hours': 1, 'duration_seconds': 3600,
                 'risk_summary': {'weather_complete': True, 'severe_miles': 25, 'high_miles': 0, 'average_risk_score': 4}}
        best, _ = recommend_best_route([unknown, known])
        self.assertEqual(best['id'], 'known')
        self.assertFalse(unknown['is_recommended'])
        best, routes = recommend_best_route([unknown])
        self.assertIsNone(best)
        self.assertFalse(routes[0]['is_recommended'])

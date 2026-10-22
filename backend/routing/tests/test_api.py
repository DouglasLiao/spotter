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

import unittest
from fastapi.testclient import TestClient
from app.api import app

client = TestClient(app)


class TestAPI(unittest.TestCase):
    def test_health_endpoint(self):
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("crm_records", data)
        self.assertIn("calendar_records", data)

    def test_matches_endpoint(self):
        response = client.get("/matches?threshold=0.8")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("threshold", data)
        self.assertIn("count", data)
        self.assertIn("matches", data)
        self.assertIsInstance(data["matches"], list)

    def test_matches_endpoint_with_limit(self):
        response = client.get("/matches?threshold=0.5&limit=5")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertLessEqual(len(data["matches"]), 5)

    def test_pair_endpoint_existing(self):
        response = client.get("/pair?crm_id=CRM-1001&calendar_id=CAL-A1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("score", data)
        self.assertIn("features", data)

    def test_pair_endpoint_nonexistent(self):
        response = client.get("/pair?crm_id=NONEXISTENT&calendar_id=CAL-A1")
        self.assertEqual(response.status_code, 404)

    def test_evaluate_endpoint(self):
        response = client.get("/evaluate?threshold=0.6")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("precision", data)
        self.assertIn("recall", data)
        self.assertIn("f1", data)
        self.assertIn("accuracy", data)
        self.assertIn("details", data)


if __name__ == '__main__':
    unittest.main()
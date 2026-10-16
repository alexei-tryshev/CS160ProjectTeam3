import unittest

from app import create_app


class WellnessTrackerTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "USE_MEMORY_DB": True, "SECRET_KEY": "test"})
        self.client = self.app.test_client()

    def test_dashboard_links_to_first_wave_features(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Nutrition tracking", body)
        self.assertIn("Water intake tracking", body)
        self.assertIn("Fitness logging", body)
        self.assertIn("Weight tracking", body)

    def test_blueprints_are_registered(self):
        self.assertIn("main", self.app.blueprints)
        self.assertIn("tracking", self.app.blueprints)
        self.assertIn("api", self.app.blueprints)
        self.assertIn("auth", self.app.blueprints)

        endpoints = {rule.endpoint for rule in self.app.url_map.iter_rules()}
        self.assertIn("main.home", endpoints)
        self.assertIn("tracking.feature_page", endpoints)
        self.assertIn("api.entries_api", endpoints)

    def test_api_accepts_and_returns_weight_entry(self):
        response = self.client.post(
            "/api/entries/weight",
            json={"date": "2026-10-15", "weight_kg": 70.5},
        )
        self.assertEqual(response.status_code, 201)
        entry = response.get_json()["entry"]
        self.assertEqual(entry["feature"], "weight")
        self.assertEqual(entry["data"]["weight_kg"], 70.5)

        listing = self.client.get("/api/entries/weight")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.get_json()["entries"]), 1)

    def test_api_rejects_negative_steps(self):
        response = self.client.post(
            "/api/entries/steps",
            json={"date": "2026-10-15", "steps": -1},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("cannot be negative", response.get_json()["errors"][0])

    def test_html_form_saves_water_entry(self):
        response = self.client.post(
            "/water",
            data={"date": "2026-10-15", "amount_ml": "750"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("750", response.get_data(as_text=True))

    def test_unknown_feature_returns_not_found(self):
        response = self.client.get("/api/entries/sleep")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()

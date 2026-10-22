import unittest

from app import create_app
from schema import (
    ENTRIES_COLLECTION,
    ENTRY_INDEXES,
    USER_INDEXES,
    USERS_COLLECTION,
    validate_entry_document_shape,
)


class WellnessTrackerTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "USE_MEMORY_DB": True,
                "SECRET_KEY": "test",
            }
        )

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

        endpoints = {
            rule.endpoint
            for rule in self.app.url_map.iter_rules()
        }

        self.assertIn("main.home", endpoints)
        self.assertIn(
            "tracking.feature_page",
            endpoints,
        )
        self.assertIn(
            "api.entries_api",
            endpoints,
        )

    def test_api_accepts_and_returns_weight_entry(self):
        response = self.client.post(
            "/api/entries/weight",
            json={
                "date": "2026-10-15",
                "weight_kg": 70.5,
            },
        )

        self.assertEqual(response.status_code, 201)

        entry = response.get_json()["entry"]

        self.assertEqual(entry["feature"], "weight")
        self.assertEqual(
            entry["data"]["weight_kg"],
            70.5,
        )
        self.assertEqual(
            entry["date"],
            "2026-10-15",
        )
        self.assertIn("created_at", entry)

        self.assertEqual(
            validate_entry_document_shape(entry),
            [],
        )

        listing = self.client.get(
            "/api/entries/weight"
        )

        self.assertEqual(listing.status_code, 200)
        self.assertEqual(
            len(listing.get_json()["entries"]),
            1,
        )

    def test_schema_defines_collections_and_indexes(self):
        self.assertEqual(
            ENTRIES_COLLECTION,
            "entries",
        )
        self.assertEqual(
            USERS_COLLECTION,
            "users",
        )

        entry_index_names = {
            index["name"]
            for index in ENTRY_INDEXES
        }

        self.assertIn(
            "entries_by_user_feature_date",
            entry_index_names,
        )

        self.assertIn(
            "entries_by_user_created_at",
            entry_index_names,
        )

        user_index = USER_INDEXES[0]

        self.assertEqual(
            user_index["name"],
            "users_by_email",
        )
        self.assertTrue(user_index["unique"])

    def test_schema_rejects_missing_payload_fields(self):
        errors = validate_entry_document_shape(
            {
                "feature": "water",
                "user_id": "demo-user",
                "date": "2026-10-15",
                "data": {
                    "date": "2026-10-15",
                },
                "created_at": (
                    "2026-10-15T16:00:00+00:00"
                ),
            }
        )

        self.assertIn(
            "Missing data field: amount_ml.",
            errors,
        )

    def test_schema_rejects_different_dates(self):
        errors = validate_entry_document_shape(
            {
                "feature": "weight",
                "user_id": "demo-user",
                "date": "2026-10-15",
                "data": {
                    "date": "2026-10-16",
                    "weight_kg": 70.5,
                },
                "created_at": (
                    "2026-10-15T16:00:00+00:00"
                ),
            }
        )

        self.assertIn(
            "The top-level date must match data.date.",
            errors,
        )

    def test_api_rejects_negative_steps(self):
        response = self.client.post(
            "/api/entries/steps",
            json={
                "date": "2026-10-15",
                "steps": -1,
            },
        )

        self.assertEqual(response.status_code, 400)

        self.assertIn(
            "cannot be negative",
            response.get_json()["errors"][0],
        )

    def test_html_form_saves_water_entry(self):
        response = self.client.post(
            "/water",
            data={
                "date": "2026-10-15",
                "amount_ml": "750",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "750",
            response.get_data(as_text=True),
        )

    def test_unknown_feature_returns_not_found(self):
        response = self.client.get(
            "/api/entries/sleep"
        )

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
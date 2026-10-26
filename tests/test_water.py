import json
import re
import unittest
from datetime import date

from app import create_app


class WaterPageTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "USE_MEMORY_DB": True,
                "SECRET_KEY": "test",
            }
        )

        self.client = self.app.test_client()
        self.repo = self.app.extensions["repository"]

    def test_page_has_wireframe_copy_and_quick_add_buttons(self):
        body = self.client.get("/water").get_data(as_text=True)

        self.assertIn("Water intake", body)
        self.assertIn("Record the amount of water you drink each day.", body)

        for amount in (250, 500, 750):
            self.assertIn(
                f'type="button" data-amount="{amount}" data-target="amount_ml"',
                body,
            )
            self.assertIn(f"+{amount} mL", body)

        self.assertIn(
            f'name="date" type="date" value="{date.today().isoformat()}"',
            body,
        )
        self.assertIn('href="/water" aria-current="page"', body)

    def test_post_saves_entry_and_redirects(self):
        response = self.client.post(
            "/water",
            data={"date": "2026-10-15", "amount_ml": "750"},
        )

        self.assertEqual(response.status_code, 302)

        entries = self.repo.list_entries("water", "demo-user")

        self.assertEqual(entries[0]["data"], {"date": "2026-10-15", "amount_ml": 750})
        self.assertIn("Entry saved.", self.client.get("/water").get_data(as_text=True))

    def test_invalid_post_rerenders_with_errors_and_values(self):
        response = self.client.post(
            "/water",
            data={"date": "2026-10-15", "amount_ml": "-3"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Amount cannot be negative.", response.get_data(as_text=True))
        self.assertEqual(self.repo.list_entries("water", "demo-user"), [])

    def test_edit_mode_prefills_and_update_changes_existing_entry(self):
        entry = self.repo.create_entry(
            "water", "demo-user", {"date": "2026-10-15", "amount_ml": 500}
        )

        body = self.client.get(f"/water?edit={entry['id']}").get_data(as_text=True)

        self.assertIn("Update entry", body)
        self.assertIn('href="/water">Cancel', body)
        self.assertIn(f'name="entry_id" value="{entry["id"]}"', body)
        self.assertIn('value="500"', body)

        self.client.post(
            "/water",
            data={"entry_id": entry["id"], "date": "2026-10-16", "amount_ml": "600"},
        )

        entries = self.repo.list_entries("water", "demo-user")

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["data"], {"date": "2026-10-16", "amount_ml": 600})

    def test_delete_removes_entry_with_confirm_prompt(self):
        entry = self.repo.create_entry(
            "water", "demo-user", {"date": "2026-10-15", "amount_ml": 500}
        )

        body = self.client.get("/water").get_data(as_text=True)

        self.assertIn("return confirm('Delete this entry?')", body)
        self.assertIn(f'action="/water/entries/{entry["id"]}/delete"', body)

        response = self.client.post(
            f"/water/entries/{entry['id']}/delete",
            follow_redirects=True,
        )

        self.assertIn("Entry deleted.", response.get_data(as_text=True))
        self.assertEqual(self.repo.list_entries("water", "demo-user"), [])

    def test_unknown_and_cross_feature_ids_show_not_found(self):
        weight = self.repo.create_entry(
            "weight", "demo-user", {"date": "2026-10-15", "weight_kg": 70.0}
        )

        response = self.client.get("/water?edit=nope")

        self.assertEqual(response.status_code, 404)
        self.assertIn("Entry not found.", response.get_data(as_text=True))

        response = self.client.post(
            f"/water/entries/{weight['id']}/delete",
            follow_redirects=True,
        )

        self.assertIn("Entry not found.", response.get_data(as_text=True))
        self.assertIsNotNone(self.repo.get_entry(weight["id"], "weight", "demo-user"))

        response = self.client.post(
            "/water",
            data={"entry_id": "nope", "date": "2026-10-15", "amount_ml": "1"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Entry not found.", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()

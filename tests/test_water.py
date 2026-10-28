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

        for amount in (8, 16, 24):
            self.assertIn(
                f'type="button" data-amount="{amount}" data-target="amount_oz"',
                body,
            )
            self.assertIn(f"+{amount} fl oz", body)

        self.assertIn(
            f'name="date" type="date" value="{date.today().isoformat()}"',
            body,
        )
        self.assertIn('href="/water" aria-current="page"', body)

    def test_post_saves_entry_and_redirects(self):
        response = self.client.post(
            "/water",
            data={"date": "2026-10-15", "amount_oz": "24"},
        )

        self.assertEqual(response.status_code, 302)

        entries = self.repo.list_entries("water", "demo-user")

        self.assertEqual(entries[0]["data"], {"date": "2026-10-15", "amount_oz": 24})
        self.assertIn("Entry saved.", self.client.get("/water").get_data(as_text=True))

    def test_invalid_post_rerenders_with_errors_and_values(self):
        response = self.client.post(
            "/water",
            data={"date": "2026-10-15", "amount_oz": "-3"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Amount cannot be negative.", response.get_data(as_text=True))
        self.assertEqual(self.repo.list_entries("water", "demo-user"), [])

    def test_edit_mode_prefills_and_update_changes_existing_entry(self):
        entry = self.repo.create_entry(
            "water", "demo-user", {"date": "2026-10-15", "amount_oz": 16}
        )

        body = self.client.get(f"/water?edit={entry['id']}").get_data(as_text=True)

        self.assertIn("Update entry", body)
        self.assertIn('href="/water">Cancel', body)
        self.assertIn(f'name="entry_id" value="{entry["id"]}"', body)
        self.assertIn('value="16"', body)

        self.client.post(
            "/water",
            data={"entry_id": entry["id"], "date": "2026-10-16", "amount_oz": "20"},
        )

        entries = self.repo.list_entries("water", "demo-user")

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["data"], {"date": "2026-10-16", "amount_oz": 20})

    def test_delete_removes_entry_with_confirm_prompt(self):
        entry = self.repo.create_entry(
            "water", "demo-user", {"date": "2026-10-15", "amount_oz": 16}
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
            "weight", "demo-user", {"date": "2026-10-15", "weight_lb": 170.0}
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
            data={"entry_id": "nope", "date": "2026-10-15", "amount_oz": "1"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Entry not found.", response.get_data(as_text=True))

    def test_today_card_shows_total_against_default_goal(self):
        today = date.today().isoformat()

        self.repo.create_entry("water", "demo-user", {"date": today, "amount_oz": 40})
        self.repo.create_entry("water", "demo-user", {"date": today, "amount_oz": 16})
        self.repo.create_entry("water", "demo-user", {"date": "2000-01-01", "amount_oz": 99})

        body = self.client.get("/water").get_data(as_text=True)

        self.assertIn(">56 <", body)
        self.assertIn("/ 64 fl oz", body)
        self.assertIn("88% of daily goal", body)
        self.assertIn('style="width: 88%"', body)
        self.assertIn("Edit goal", body)

    def test_progress_bar_caps_at_full_when_goal_exceeded(self):
        self.repo.create_entry(
            "water", "demo-user", {"date": date.today().isoformat(), "amount_oz": 96}
        )

        body = self.client.get("/water").get_data(as_text=True)

        self.assertIn("150% of daily goal", body)
        self.assertIn('style="width: 100%"', body)

    def test_goal_update_persists(self):
        response = self.client.post(
            "/water/goal",
            data={"water_goal_oz": "80"},
            follow_redirects=True,
        )

        body = response.get_data(as_text=True)

        self.assertIn("Daily goal updated.", body)
        self.assertIn("/ 80 fl oz", body)
        self.assertEqual(self.repo.get_water_goal("demo-user"), 80)

    def test_invalid_goal_is_rejected_and_goal_unchanged(self):
        self.repo.set_water_goal("demo-user", 80)

        for bad in ("", "0", "-5", "2.5", "abc"):
            body = self.client.post(
                "/water/goal",
                data={"water_goal_oz": bad},
                follow_redirects=True,
            ).get_data(as_text=True)

            self.assertIn("Daily goal must be a whole number greater than zero.", body)

        self.assertEqual(self.repo.get_water_goal("demo-user"), 80)

    def test_chart_data_has_seven_daily_totals(self):
        self.repo.create_entry(
            "water", "demo-user", {"date": date.today().isoformat(), "amount_oz": 12}
        )

        body = self.client.get("/water").get_data(as_text=True)

        self.assertIn('data-chart="water-bar"', body)
        self.assertIn("chart.js@4.4.1", body)

        payload = json.loads(
            re.search(r'id="chart-data"[^>]*>(.*?)</script>', body, re.S).group(1)
        )

        self.assertEqual(len(payload), 7)
        self.assertEqual(
            payload[-1],
            {"date": date.today().isoformat(), "total_oz": 12},
        )

    def test_oversized_amount_and_goal_are_rejected_with_messages(self):
        response = self.client.post(
            "/water",
            data={"date": "2026-10-15", "amount_oz": "99999999999999999999"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Amount must be at most 350 fl oz.", response.get_data(as_text=True))
        self.assertEqual(self.repo.list_entries("water", "demo-user"), [])

        body = self.client.post(
            "/water/goal",
            data={"water_goal_oz": "701"},
            follow_redirects=True,
        ).get_data(as_text=True)

        self.assertIn("Daily goal must be at most 700 fl oz.", body)
        self.assertIsNone(self.repo.get_water_goal("demo-user"))


if __name__ == "__main__":
    unittest.main()

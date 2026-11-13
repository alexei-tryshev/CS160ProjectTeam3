import json
import re
import unittest
from datetime import date, timedelta

from app import create_app
from tests.auth_helpers import log_in


TODAY = date.today().isoformat()
TOMORROW = (date.today() + timedelta(days=1)).isoformat()


def chart_payload(body):
    return json.loads(
        re.search(r'id="chart-data"[^>]*>(.*?)</script>', body, re.S).group(1)
    )


def tile_value(body, label):
    match = re.search(
        r'<p class="tile-label">{}</p>\s*<p class="tile-value">([^<]*)</p>'.format(
            re.escape(label)
        ),
        body,
    )

    return match.group(1).strip()


class StepsPageTestCase(unittest.TestCase):

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
        self.user_id = log_in(self.client, self.repo)

    def add(self, day, count, user_id=None):
        return self.repo.create_entry(
            "steps", user_id or self.user_id, {"date": day, "steps": count}
        )

    def test_page_copy_and_active_nav(self):
        body = self.client.get("/steps").get_data(as_text=True)

        self.assertIn("Record the steps you take each day.", body)
        self.assertIn("Log steps", body)
        self.assertIn('name="steps"', body)
        self.assertIn(f'name="date" type="date" value="{TODAY}"', body)
        self.assertIn('href="/steps" aria-current="page"', body)
        self.assertIn("No entries yet. Add the first one above.", body)

    def test_post_saves_entry_and_redirects(self):
        response = self.client.post(
            "/steps",
            data={"date": "2026-10-15", "steps": "4200"},
        )

        self.assertEqual(response.status_code, 302)

        entries = self.repo.list_entries("steps", self.user_id)

        self.assertEqual(entries[0]["data"], {"date": "2026-10-15", "steps": 4200})

        body = self.client.get("/steps").get_data(as_text=True)

        self.assertIn("Entry saved.", body)
        self.assertIn("<td>4,200</td>", body)

    def test_over_cap_rejected(self):
        response = self.client.post(
            "/steps",
            data={"date": "2026-10-15", "steps": "100001"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Steps must be at most 100,000.", response.get_data(as_text=True))
        self.assertEqual(self.repo.list_entries("steps", self.user_id), [])

    def test_edit_prefills_and_updates_existing_entry(self):
        entry = self.add("2026-10-15", 4200)

        body = self.client.get(f"/steps?edit={entry['id']}").get_data(as_text=True)

        self.assertIn("Update entry", body)
        self.assertIn('href="/steps">Cancel', body)
        self.assertIn(f'name="entry_id" value="{entry["id"]}"', body)
        self.assertIn('value="4200"', body)

        self.client.post(
            "/steps",
            data={"entry_id": entry["id"], "date": "2026-10-16", "steps": "5000"},
        )

        entries = self.repo.list_entries("steps", self.user_id)

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["data"], {"date": "2026-10-16", "steps": 5000})

    def test_delete_removes_entry(self):
        entry = self.add("2026-10-15", 4200)

        body = self.client.get("/steps").get_data(as_text=True)

        self.assertIn("return confirm('Delete this entry?')", body)
        self.assertIn(f'action="/steps/entries/{entry["id"]}/delete"', body)

        response = self.client.post(
            f"/steps/entries/{entry['id']}/delete",
            follow_redirects=True,
        )

        self.assertIn("Entry deleted.", response.get_data(as_text=True))
        self.assertEqual(self.repo.list_entries("steps", self.user_id), [])

    def test_other_users_entry_cannot_be_edited_or_deleted(self):
        other = self.repo.create_user("other@example.com", "hash")
        entry = self.add("2026-10-15", 4200, user_id=other["id"])

        response = self.client.get(f"/steps?edit={entry['id']}")

        self.assertEqual(response.status_code, 404)
        self.assertIn("Entry not found.", response.get_data(as_text=True))

        self.client.post(f"/steps/entries/{entry['id']}/delete")

        self.assertIsNotNone(self.repo.get_entry(entry["id"], "steps", other["id"]))

    def test_today_and_week_tiles_sum_multiple_entries(self):
        self.add(TODAY, 3000)
        self.add(TODAY, 1500)
        self.add("2000-01-01", 99999)

        body = self.client.get("/steps").get_data(as_text=True)

        self.assertEqual(tile_value(body, "Today"), "4,500")

        monday = date.today() - timedelta(days=date.today().weekday())

        if monday != date.today():
            self.add(monday.isoformat(), 1000)
            body = self.client.get("/steps").get_data(as_text=True)

            self.assertEqual(tile_value(body, "Today"), "4,500")
            self.assertEqual(tile_value(body, "This week"), "5,500")
        else:
            self.assertEqual(tile_value(body, "This week"), "4,500")

    def test_future_entry_not_in_today_or_week_tiles_or_chart(self):
        self.add(TOMORROW, 7777)

        body = self.client.get("/steps").get_data(as_text=True)

        self.assertEqual(tile_value(body, "Today"), "0")
        self.assertEqual(tile_value(body, "This week"), "0")
        self.assertTrue(
            all(point["total_steps"] == 0 for point in chart_payload(body))
        )
        self.assertIn("<td>7,777</td>", body)

    def test_chart_json_range(self):
        self.add(TODAY, 800)

        body = self.client.get("/steps").get_data(as_text=True)

        self.assertIn('data-chart="steps-bar"', body)

        points = chart_payload(body)

        self.assertEqual(len(points), 7)
        self.assertEqual(points[-1], {"date": TODAY, "total_steps": 800})

        month = chart_payload(self.client.get("/steps?range=1m").get_data(as_text=True))

        self.assertEqual(len(month), 30)

        fallback = chart_payload(self.client.get("/steps?range=zzz").get_data(as_text=True))

        self.assertEqual(len(fallback), 7)

    def test_fitness_redirects_to_steps(self):
        response = self.client.get("/fitness")

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/steps"))


if __name__ == "__main__":
    unittest.main()

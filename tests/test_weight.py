import json
import re
import unittest
from datetime import date, timedelta

from app import create_app


def d(days_ago):
    return (date.today() - timedelta(days=days_ago)).isoformat()


def chart_payload(body):
    return json.loads(
        re.search(r'id="chart-data"[^>]*>(.*?)</script>', body, re.S).group(1)
    )


class WeightPageTestCase(unittest.TestCase):

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

    def add(self, days_ago, weight_kg):
        return self.repo.create_entry(
            "weight", "demo-user", {"date": d(days_ago), "weight_kg": weight_kg}
        )

    def test_page_copy_and_layout(self):
        body = self.client.get("/weight").get_data(as_text=True)

        self.assertIn("Weight tracking", body)
        self.assertIn(
            "Record a body-weight measurement and see how it changes over time.",
            body,
        )

        for label in ("1W", "1M", "3M", "All", "Latest", "Change (period)"):
            self.assertIn(label, body)

        self.assertNotIn("Goal", body)
        self.assertIn('href="/weight" aria-current="page"', body)

    def test_tiles_rows_and_chart_for_one_week(self):
        self.add(20, 70.0)
        self.add(5, 69.3)
        self.add(3, 68.8)
        self.add(0, 68.5)

        body = self.client.get("/weight").get_data(as_text=True)

        self.assertIn("68.5 kg", body)       # Latest
        self.assertIn("−0.8 kg", body)  # 69.3 -> 68.5 within 1W
        self.assertIn("−0.3", body)     # row change
        self.assertIn("−0.7", body)     # oldest 1W row still compares to d(20)
        self.assertEqual(
            [point["weight_kg"] for point in chart_payload(body)],
            [69.3, 68.8, 68.5],
        )
        self.assertIn('data-chart="weight-line"', body)

    def test_range_all_and_unknown_range(self):
        self.add(60, 72.0)
        self.add(0, 70.0)

        self.assertIn(
            "−2.0 kg",
            self.client.get("/weight?range=all").get_data(as_text=True),
        )

        body = self.client.get("/weight?range=xyz").get_data(as_text=True)

        self.assertIn('class="is-active" href="/weight?range=1w"', body)

    def test_sparse_data_shows_dashes(self):
        response = self.client.get("/weight")

        self.assertEqual(response.status_code, 200)
        self.assertIn("No entries yet", response.get_data(as_text=True))

        self.add(30, 70.0)

        body = self.client.get("/weight").get_data(as_text=True)

        self.assertIn("70.0 kg", body)  # Latest uses all entries
        self.assertIn("— kg", body)     # no period change in 1W

    def test_save_edit_delete_and_not_found(self):
        response = self.client.post(
            "/weight",
            data={"date": "2026-10-15", "weight_kg": "70.5"},
        )

        self.assertEqual(response.status_code, 302)

        entry = self.repo.list_entries("weight", "demo-user")[0]

        self.assertIn(
            "Update entry",
            self.client.get(f"/weight?edit={entry['id']}").get_data(as_text=True),
        )

        self.client.post(
            "/weight",
            data={"entry_id": entry["id"], "date": "2026-10-15", "weight_kg": "70.1"},
        )

        self.assertEqual(
            self.repo.get_entry(entry["id"], "weight", "demo-user")["data"]["weight_kg"],
            70.1,
        )
        self.assertEqual(
            self.client.post(
                "/weight",
                data={"date": "2026-10-15", "weight_kg": "0"},
            ).status_code,
            400,
        )
        self.assertEqual(self.client.get("/weight?edit=nope").status_code, 404)

        self.client.post(f"/weight/entries/{entry['id']}/delete")

        self.assertEqual(self.repo.list_entries("weight", "demo-user"), [])


if __name__ == "__main__":
    unittest.main()

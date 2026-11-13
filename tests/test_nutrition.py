import json
import re
import unittest
from datetime import date, timedelta

from app import create_app
from tests.auth_helpers import log_in

TODAY = date.today().isoformat()
TOMORROW = (date.today() + timedelta(days=1)).isoformat()
MONDAY = (date.today() - timedelta(days=date.today().weekday())).isoformat()
FIRST = date.today().replace(day=1).isoformat()


def chart_payload(body):
    return json.loads(
        re.search(r'id="chart-data"[^>]*>(.*?)</script>', body, re.S).group(1)
    )


def macro_chart_payload(body):
    return json.loads(
        re.search(
            r'id="macro-chart-data"[^>]*>(.*?)</script>', body, re.S
        ).group(1)
    )


def tile_value(body, label):
    match = re.search(
        r'<p class="tile-label">{}</p>\s*<p class="tile-value">([^<]*)</p>'.format(
            re.escape(label)
        ),
        body,
    )
    return match.group(1).strip()


class NutritionPageTestCase(unittest.TestCase):
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

    def add(
        self,
        day,
        food="Oatmeal",
        calories=300.0,
        protein_g=10.0,
        carbs_g=50.0,
        fat_g=5.0,
        user_id=None,
    ):
        return self.repo.create_entry(
            "nutrition",
            user_id or self.user_id,
            {
                "date": day,
                "food": food,
                "calories": calories,
                "protein_g": protein_g,
                "carbs_g": carbs_g,
                "fat_g": fat_g,
            },
        )

    def test_page_copy_and_active_nav(self):
        body = self.client.get("/nutrition").get_data(as_text=True)
        self.assertIn(
            "Record the food you eat and track your daily calorie and macronutrient intake.",
            body,
        )
        self.assertIn("Log food", body)
        self.assertIn("Macronutrient intake", body)
        for field in ("food", "calories", "protein_g", "carbs_g", "fat_g"):
            self.assertIn(f'name="{field}"', body)
        self.assertIn(f'name="date" type="date" value="{TODAY}"', body)
        self.assertIn('href="/nutrition" aria-current="page"', body)
        self.assertIn("No entries yet. Add the first one above.", body)

    def test_dashboard_links_to_macros_and_macros_route_redirects(self):
        dashboard = self.client.get("/").get_data(as_text=True)
        self.assertIn("Macronutrient tracking", dashboard)
        self.assertIn(
            "See your daily, weekly, and monthly protein, carbohydrate, and fat intake.",
            dashboard,
        )
        response = self.client.get("/macros")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/nutrition#macros"))

    def test_post_saves_entry_and_redirects(self):
        response = self.client.post(
            "/nutrition",
            data={
                "date": "2026-10-15",
                "food": "Greek Yogurt",
                "calories": "150",
                "protein_g": "15",
                "carbs_g": "12",
                "fat_g": "4.5",
            },
        )
        self.assertEqual(response.status_code, 302)
        entries = self.repo.list_entries("nutrition", self.user_id)
        self.assertEqual(
            entries[0]["data"],
            {
                "date": "2026-10-15",
                "food": "Greek Yogurt",
                "calories": 150.0,
                "protein_g": 15.0,
                "carbs_g": 12.0,
                "fat_g": 4.5,
            },
        )
        body = self.client.get("/nutrition").get_data(as_text=True)
        self.assertIn("Entry saved.", body)
        self.assertIn("<td>Greek Yogurt</td>", body)
        self.assertIn("<td>150</td>", body)
        self.assertIn("<td>4.5</td>", body)

    def test_invalid_post_rerenders_with_errors(self):
        response = self.client.post(
            "/nutrition",
            data={
                "date": "2026-10-15",
                "food": "  ",
                "calories": "-10",
                "protein_g": "10",
                "carbs_g": "20",
                "fat_g": "5",
            },
        )
        self.assertEqual(response.status_code, 400)
        body = response.get_data(as_text=True)
        self.assertIn("Food is required.", body)
        self.assertIn("Calories cannot be negative.", body)
        self.assertEqual(self.repo.list_entries("nutrition", self.user_id), [])

    def test_edit_prefills_and_updates_existing_entry(self):
        entry = self.add("2026-10-15", food="Apple", calories=95.0)
        body = self.client.get(f"/nutrition?edit={entry['id']}").get_data(as_text=True)
        self.assertIn("Edit entry", body)
        self.assertIn("Update entry", body)
        self.assertIn('href="/nutrition">Cancel', body)
        self.assertIn(f'name="entry_id" value="{entry["id"]}"', body)
        self.assertIn('value="Apple"', body)

        self.client.post(
            "/nutrition",
            data={
                "entry_id": entry["id"],
                "date": "2026-10-16",
                "food": "Large Apple",
                "calories": "120",
                "protein_g": "0.6",
                "carbs_g": "30",
                "fat_g": "0.4",
            },
        )
        entries = self.repo.list_entries("nutrition", self.user_id)
        self.assertEqual(len(entries), 1)
        self.assertEqual(
            entries[0]["data"],
            {
                "date": "2026-10-16",
                "food": "Large Apple",
                "calories": 120.0,
                "protein_g": 0.6,
                "carbs_g": 30.0,
                "fat_g": 0.4,
            },
        )

    def test_delete_removes_entry(self):
        entry = self.add("2026-10-15")
        body = self.client.get("/nutrition").get_data(as_text=True)
        self.assertIn("return confirm('Delete this entry?')", body)
        self.assertIn(f'action="/nutrition/entries/{entry["id"]}/delete"', body)

        response = self.client.post(
            f"/nutrition/entries/{entry['id']}/delete",
            follow_redirects=True,
        )
        self.assertIn("Entry deleted.", response.get_data(as_text=True))
        self.assertEqual(self.repo.list_entries("nutrition", self.user_id), [])

    def test_other_users_entry_cannot_be_edited_or_deleted(self):
        other = self.repo.create_user("other@example.com", "hash")
        entry = self.add("2026-10-15", user_id=other["id"])

        response = self.client.get(f"/nutrition?edit={entry['id']}")
        self.assertEqual(response.status_code, 404)
        self.assertIn("Entry not found.", response.get_data(as_text=True))

        self.client.post(f"/nutrition/entries/{entry['id']}/delete")
        self.assertIsNotNone(self.repo.get_entry(entry["id"], "nutrition", other["id"]))

    def test_today_and_week_tiles_sum_multiple_entries(self):
        self.add(TODAY, food="Breakfast", calories=450)
        self.add(TODAY, food="Lunch", calories=750.5)
        self.add("2000-01-01", food="Old Meal", calories=9999)
        body = self.client.get("/nutrition").get_data(as_text=True)
        self.assertEqual(tile_value(body, "Today"), "1,200.5 kcal")

        if MONDAY != TODAY:
            self.add(MONDAY, food="Monday Snack", calories=200)
            body = self.client.get("/nutrition").get_data(as_text=True)
            self.assertEqual(tile_value(body, "Today"), "1,200.5 kcal")
            self.assertEqual(tile_value(body, "This week"), "1,400.5 kcal")
        else:
            self.assertEqual(tile_value(body, "This week"), "1,200.5 kcal")

    def test_macronutrient_tiles_and_percentages_for_today(self):
        self.add(TODAY, food="Meal 1", protein_g=30.0, carbs_g=50.0, fat_g=20.0)
        self.add(TODAY, food="Meal 2", protein_g=10.0, carbs_g=50.0, fat_g=40.0)
        body = self.client.get("/nutrition").get_data(as_text=True)
        self.assertEqual(tile_value(body, "Protein"), "40 g")
        self.assertEqual(tile_value(body, "Carbohydrates"), "100 g")
        self.assertEqual(tile_value(body, "Fat"), "60 g")
        self.assertIn("20% of macros", body)
        self.assertIn("50% of macros", body)
        self.assertIn("30% of macros", body)

    def test_macronutrient_period_switch_today_week_month(self):
        self.add(TODAY, food="Today Meal", protein_g=25.0, carbs_g=40.0, fat_g=10.0)
        self.add(FIRST, food="First of Month", protein_g=50.0, carbs_g=80.0, fat_g=20.0)

        month_body = self.client.get("/nutrition?period=month").get_data(as_text=True)
        self.assertEqual(tile_value(month_body, "Protein"), "75 g")
        self.assertEqual(tile_value(month_body, "Carbohydrates"), "120 g")
        self.assertEqual(tile_value(month_body, "Fat"), "30 g")

        if FIRST != TODAY:
            today_body = self.client.get("/nutrition?period=today").get_data(as_text=True)
            self.assertEqual(tile_value(today_body, "Protein"), "25 g")
            fallback_body = self.client.get("/nutrition?period=zzz").get_data(as_text=True)
            self.assertEqual(tile_value(fallback_body, "Protein"), "25 g")

    def test_future_entry_not_in_today_or_week_tiles_or_charts(self):
        self.add(
            TOMORROW,
            food="Future Meal",
            calories=800,
            protein_g=40,
            carbs_g=90,
            fat_g=30,
        )
        body = self.client.get("/nutrition").get_data(as_text=True)
        self.assertEqual(tile_value(body, "Today"), "0 kcal")
        self.assertEqual(tile_value(body, "This week"), "0 kcal")
        self.assertEqual(tile_value(body, "Protein"), "0 g")
        self.assertEqual(tile_value(body, "Carbohydrates"), "0 g")
        self.assertEqual(tile_value(body, "Fat"), "0 g")
        self.assertTrue(
            all(point["total_calories"] == 0 for point in chart_payload(body))
        )
        self.assertTrue(
            all(point["protein_g"] == 0 for point in macro_chart_payload(body))
        )
        self.assertIn("<td>Future Meal</td>", body)

    def test_chart_and_macro_chart_json_range(self):
        self.add(
            TODAY,
            food="Dinner",
            calories=650,
            protein_g=35.5,
            carbs_g=60.0,
            fat_g=22.0,
        )
        body = self.client.get("/nutrition").get_data(as_text=True)
        self.assertIn('data-chart="nutrition-bar"', body)
        self.assertIn('data-chart="macros-bar"', body)

        points = chart_payload(body)
        self.assertEqual(len(points), 7)
        self.assertEqual(points[-1], {"date": TODAY, "total_calories": 650.0})

        macro_points = macro_chart_payload(body)
        self.assertEqual(len(macro_points), 7)
        self.assertEqual(
            macro_points[-1],
            {
                "date": TODAY,
                "protein_g": 35.5,
                "carbs_g": 60.0,
                "fat_g": 22.0,
            },
        )

        month = macro_chart_payload(
            self.client.get("/nutrition?range=1m").get_data(as_text=True)
        )
        self.assertEqual(len(month), 30)


if __name__ == "__main__":
    unittest.main()
import unittest
from datetime import date

from app import create_app
from meal_plan import daily_targets, remaining, suggest_meals, validate_plan
from tests.auth_helpers import log_in

TODAY = date.today().isoformat()


class MealPlanMathTestCase(unittest.TestCase):
    def test_maintain_targets(self):
        targets = daily_targets({"goal": "maintain", "activity": "moderate", "weight_lb": 150})
        self.assertEqual(targets["calories"], 2250)
        self.assertEqual(targets["protein_g"], 120)
        self.assertEqual(targets["fat_g"], 62)

    def test_cut_is_500_below_maintain(self):
        base = {"activity": "moderate", "weight_lb": 180}
        cut = daily_targets(dict(base, goal="cut"))
        keep = daily_targets(dict(base, goal="maintain"))
        self.assertEqual(keep["calories"] - cut["calories"], 500)

    def test_calories_never_below_minimum(self):
        targets = daily_targets({"goal": "cut", "activity": "light", "weight_lb": 100})
        self.assertEqual(targets["calories"], 1200)

    def test_validate_rejects_bad_input(self):
        plan, errors = validate_plan({"goal": "x", "activity": "moderate", "weight_lb": "abc"})
        self.assertIsNone(plan)
        self.assertEqual(len(errors), 2)

    def test_remaining_never_negative(self):
        left = remaining({"calories": 2000, "protein_g": 100}, {"calories": 2500, "protein_g": 40})
        self.assertEqual(left, {"calories": 0, "protein_g": 60})

    def test_suggestions_fit_calories_left(self):
        meals = suggest_meals({"calories": 300, "protein_g": 50})
        self.assertTrue(meals)
        self.assertTrue(all(meal["calories"] <= 300 for meal in meals))
        self.assertEqual(suggest_meals({"calories": 0, "protein_g": 0}), [])


class MealPlanPageTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "USE_MEMORY_DB": True, "SECRET_KEY": "test"})
        self.client = self.app.test_client()
        self.repo = self.app.extensions["repository"]
        self.user_id = log_in(self.client, self.repo)

    def test_requires_login(self):
        anonymous = self.app.test_client()
        response = anonymous.get("/meal-plan")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.headers["Location"])

    def test_form_prefills_latest_weight(self):
        self.repo.add_entry("weight", self.user_id, {"weight_lb": 163.5, "date": TODAY})
        body = self.client.get("/meal-plan").get_data(as_text=True)
        self.assertIn('value="163.5"', body)

    def test_save_plan_and_see_progress(self):
        self.repo.add_entry(
            "nutrition",
            self.user_id,
            {"food": "Oatmeal", "calories": 250.0, "protein_g": 20.0, "carbs_g": 30.0, "fat_g": 5.0, "date": TODAY},
        )
        response = self.client.post(
            "/meal-plan",
            data={"goal": "maintain", "activity": "moderate", "weight_lb": "150"},
        )
        self.assertEqual(response.status_code, 302)
        body = self.client.get("/meal-plan").get_data(as_text=True)
        self.assertIn("250 / 2250 kcal", body)
        self.assertIn("2000 kcal left", body)
        self.assertIn("Suggested meals", body)

    def test_invalid_plan_shows_errors(self):
        response = self.client.post("/meal-plan", data={"goal": "", "activity": "", "weight_lb": ""})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Choose a goal.", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
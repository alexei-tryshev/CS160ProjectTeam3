"""Login is required everywhere, and each user sees only their own data."""

import unittest
from datetime import date

from app import create_app
from tests.auth_helpers import log_in


TODAY = date.today().isoformat()

PAGES = ["/", "/nutrition", "/water", "/steps", "/fitness", "/weight"]


class LoggedOutAccessTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app(
            {"TESTING": True, "USE_MEMORY_DB": True, "SECRET_KEY": "test"}
        )
        self.client = self.app.test_client()
        self.repo = self.app.extensions["repository"]

    def test_pages_redirect_to_login_with_next(self):
        for path in PAGES:
            with self.subTest(path=path):
                response = self.client.get(path)

                self.assertEqual(response.status_code, 302)
                self.assertTrue(
                    response.headers["Location"].startswith("/auth/login?next=")
                )

    def test_form_posts_are_refused_and_save_nothing(self):
        posts = [
            ("/water", {"date": TODAY, "amount_oz": "12"}),
            ("/weight", {"date": TODAY, "weight_lb": "150"}),
            ("/steps", {"date": TODAY, "steps": "1000"}),
            ("/water/goal", {"water_goal_oz": "80"}),
            ("/water/entries/anything/delete", {}),
        ]

        for path, data in posts:
            with self.subTest(path=path):
                response = self.client.post(path, data=data)

                self.assertEqual(response.status_code, 302)
                self.assertIn("/auth/login", response.headers["Location"])

        for feature in ("water", "weight", "steps"):
            self.assertEqual(self.repo.list_entries(feature, None), [])

    def test_api_returns_401_but_health_stays_public(self):
        self.assertEqual(self.client.get("/api/entries/water").status_code, 401)
        self.assertEqual(
            self.client.post(
                "/api/entries/water",
                json={"date": TODAY, "amount_oz": 8, "user_id": "someone"},
            ).status_code,
            401,
        )
        self.assertEqual(
            self.client.delete("/api/entries/water/x").status_code, 401
        )
        self.assertEqual(self.client.get("/api/health").status_code, 200)

    def test_login_returns_to_requested_page(self):
        redirect_to_login = self.client.get("/weight?range=1m")
        login_url = redirect_to_login.headers["Location"]

        log_in(self.client, self.repo)  # creates the user
        self.client.post("/auth/logout")

        response = self.client.post(
            login_url,
            data={"email": "tester@example.com", "password": "Password123!"},
        )

        self.assertEqual(response.headers["Location"], "/weight?range=1m")

    def test_login_ignores_offsite_next(self):
        log_in(self.client, self.repo)
        self.client.post("/auth/logout")

        for bad in ("https://evil.example", "//evil.example", "/\\evil.example"):
            with self.subTest(next=bad):
                response = self.client.post(
                    "/auth/login",
                    query_string={"next": bad},
                    data={
                        "email": "tester@example.com",
                        "password": "Password123!",
                    },
                )

                self.assertEqual(response.headers["Location"], "/")
                self.client.post("/auth/logout")

    def test_logout_ends_access(self):
        log_in(self.client, self.repo)
        self.assertEqual(self.client.get("/water").status_code, 200)

        response = self.client.post("/auth/logout")

        self.assertEqual(response.headers["Location"], "/auth/login")
        self.assertEqual(self.client.get("/water").status_code, 302)

    def test_logged_out_nav_hides_tracker_links(self):
        body = self.client.get("/auth/login").get_data(as_text=True)

        self.assertNotIn('href="/water"', body)
        self.assertIn('href="/auth/register"', body)


class UserIsolationTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app(
            {"TESTING": True, "USE_MEMORY_DB": True, "SECRET_KEY": "test"}
        )
        self.repo = self.app.extensions["repository"]

        self.alice = self.app.test_client()
        self.bob = self.app.test_client()
        self.alice_id = log_in(self.alice, self.repo, "alice@example.com")
        self.bob_id = log_in(self.bob, self.repo, "bob@example.com")

    def test_form_entries_belong_to_the_logged_in_user(self):
        self.alice.post("/water", data={"date": TODAY, "amount_oz": "33"})
        self.alice.post("/nutrition", data={
            "food": "Apple", "calories": "95", "protein_g": "0.5",
            "carbs_g": "25", "fat_g": "0.3", "date": TODAY,
        })

        self.assertEqual(len(self.repo.list_entries("water", self.alice_id)), 1)
        self.assertEqual(len(self.repo.list_entries("nutrition", self.alice_id)), 1)
        self.assertEqual(self.repo.list_entries("water", self.bob_id), [])

        self.assertNotIn("<td>33</td>", self.bob.get("/water").get_data(as_text=True))
        self.assertNotIn("Apple", self.bob.get("/nutrition").get_data(as_text=True))

    def test_other_users_entries_cannot_be_edited_or_deleted(self):
        entry = self.repo.create_entry(
            "weight", self.alice_id, {"date": TODAY, "weight_lb": 150.0}
        )

        edit = self.bob.get("/weight?edit={}".format(entry["id"]))
        self.assertEqual(edit.status_code, 404)

        self.bob.post("/weight", data={
            "entry_id": entry["id"], "date": TODAY, "weight_lb": "999",
        })
        self.bob.post("/weight/entries/{}/delete".format(entry["id"]))

        kept = self.repo.get_entry(entry["id"], "weight", self.alice_id)
        self.assertEqual(kept["data"]["weight_lb"], 150.0)

    def test_water_goal_is_per_user(self):
        self.alice.post("/water/goal", data={"water_goal_oz": "100"})

        self.assertEqual(self.repo.get_water_goal(self.alice_id), 100)
        self.assertIsNone(self.repo.get_water_goal(self.bob_id))

    def test_api_ignores_client_supplied_user_id(self):
        created = self.bob.post(
            "/api/entries/steps",
            json={"date": TODAY, "steps": 500, "user_id": self.alice_id},
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.get_json()["entry"]["user_id"], self.bob_id)
        self.assertEqual(self.repo.list_entries("steps", self.alice_id), [])

        alice_entry = self.repo.create_entry(
            "steps", self.alice_id, {"date": TODAY, "steps": 9000}
        )
        path = "/api/entries/steps/{}".format(alice_entry["id"])

        listing = self.bob.get(
            "/api/entries/steps", query_string={"user_id": self.alice_id}
        ).get_json()
        self.assertEqual(listing["user_id"], self.bob_id)
        self.assertEqual(len(listing["entries"]), 1)

        self.assertEqual(
            self.bob.get(path, query_string={"user_id": self.alice_id}).status_code,
            404,
        )
        self.assertEqual(
            self.bob.put(
                path, json={"date": TODAY, "steps": 1, "user_id": self.alice_id}
            ).status_code,
            404,
        )
        self.assertEqual(
            self.bob.delete(path, query_string={"user_id": self.alice_id}).status_code,
            404,
        )
        self.assertIsNotNone(
            self.repo.get_entry(alice_entry["id"], "steps", self.alice_id)
        )


if __name__ == "__main__":
    unittest.main()

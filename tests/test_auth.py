import unittest

from app import create_app
from werkzeug.security import check_password_hash


class AuthenticationTests(unittest.TestCase):

    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "USE_MEMORY_DB": True,
                "SECRET_KEY": "test-secret",
            }
        )

        self.client = self.app.test_client()

        self.repository = (
            self.app.extensions["repository"]
        )

    def register_test_user(self):
        response = self.client.post(
            "/auth/register",
            data={
                "email": "alex@example.com",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
            follow_redirects=True,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        return self.repository.get_user_by_email(
            "alex@example.com"
        )

    def test_registration_page_loads(self):
        response = self.client.get(
            "/auth/register"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            "Create an account",
            response.get_data(as_text=True),
        )

    def test_login_page_loads(self):
        response = self.client.get(
            "/auth/login"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            "Log in",
            response.get_data(as_text=True),
        )

    def test_registration_stores_hashed_password(self):
        user = self.register_test_user()

        self.assertIsNotNone(user)

        self.assertEqual(
            user["email"],
            "alex@example.com",
        )

        self.assertNotEqual(
            user["password_hash"],
            "Password123!",
        )

        self.assertTrue(
            check_password_hash(
                user["password_hash"],
                "Password123!",
            )
        )

        self.assertNotIn(
            "password",
            user,
        )

    def test_duplicate_registration_is_rejected(self):
        self.register_test_user()

        response = self.client.post(
            "/auth/register",
            data={
                "email": "ALEX@example.com",
                "password": "Different123!",
                "confirm_password": "Different123!",
            },
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "already exists",
            response.get_data(as_text=True),
        )

    def test_valid_login_creates_session(self):
        user = self.register_test_user()

        response = self.client.post(
            "/auth/login",
            data={
                "email": "ALEX@example.com",
                "password": "Password123!",
            },
            follow_redirects=True,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            "Logged in successfully.",
            response.get_data(as_text=True),
        )

        with self.client.session_transaction() as flask_session:
            self.assertEqual(
                flask_session.get("user_id"),
                user["id"],
            )

            self.assertEqual(
                flask_session.get("email"),
                "alex@example.com",
            )

    def test_invalid_password_does_not_create_session(self):
        self.register_test_user()

        response = self.client.post(
            "/auth/login",
            data={
                "email": "alex@example.com",
                "password": "WrongPassword!",
            },
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "Invalid email or password.",
            response.get_data(as_text=True),
        )

        with self.client.session_transaction() as flask_session:
            self.assertNotIn(
                "user_id",
                flask_session,
            )

    def test_unknown_email_does_not_create_session(self):
        response = self.client.post(
            "/auth/login",
            data={
                "email": "unknown@example.com",
                "password": "Password123!",
            },
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "Invalid email or password.",
            response.get_data(as_text=True),
        )

        with self.client.session_transaction() as flask_session:
            self.assertNotIn(
                "user_id",
                flask_session,
            )

    def test_logout_clears_session(self):
        user = self.register_test_user()

        self.client.post(
            "/auth/login",
            data={
                "email": "alex@example.com",
                "password": "Password123!",
            },
        )

        with self.client.session_transaction() as flask_session:
            self.assertEqual(
                flask_session.get("user_id"),
                user["id"],
            )

        response = self.client.post(
            "/auth/logout",
            follow_redirects=True,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            "logged out",
            response.get_data(as_text=True).lower(),
        )

        with self.client.session_transaction() as flask_session:
            self.assertNotIn(
                "user_id",
                flask_session,
            )

            self.assertNotIn(
                "email",
                flask_session,
            )


if __name__ == "__main__":
    unittest.main()
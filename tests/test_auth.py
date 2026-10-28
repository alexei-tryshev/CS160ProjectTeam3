import unittest

from app import create_app
from werkzeug.security import check_password_hash


class RegistrationTests(unittest.TestCase):

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

    def test_registration_creates_hashed_password(self):
        response = self.client.post(
            "/auth/register",
            data={
                "email": "Alex@example.com",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
            follow_redirects=True,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        user = self.repository.get_user_by_email(
            "alex@example.com"
        )

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

        self.assertIn(
            "Account created successfully.",
            response.get_data(as_text=True),
        )

    def test_duplicate_email_is_rejected(self):
        first_response = self.client.post(
            "/auth/register",
            data={
                "email": "duplicate@example.com",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
        )

        self.assertEqual(
            first_response.status_code,
            302,
        )

        second_response = self.client.post(
            "/auth/register",
            data={
                "email": "DUPLICATE@example.com",
                "password": "AnotherPassword123!",
                "confirm_password": "AnotherPassword123!",
            },
        )

        self.assertEqual(
            second_response.status_code,
            400,
        )

        self.assertIn(
            "already exists",
            second_response.get_data(as_text=True),
        )

    def test_short_password_is_rejected(self):
        response = self.client.post(
            "/auth/register",
            data={
                "email": "short@example.com",
                "password": "short",
                "confirm_password": "short",
            },
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "at least 8 characters",
            response.get_data(as_text=True),
        )

        self.assertIsNone(
            self.repository.get_user_by_email(
                "short@example.com"
            )
        )

    def test_mismatched_passwords_are_rejected(self):
        response = self.client.post(
            "/auth/register",
            data={
                "email": "mismatch@example.com",
                "password": "Password123!",
                "confirm_password": "Different123!",
            },
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "Passwords do not match",
            response.get_data(as_text=True),
        )

        self.assertIsNone(
            self.repository.get_user_by_email(
                "mismatch@example.com"
            )
        )


if __name__ == "__main__":
    unittest.main()
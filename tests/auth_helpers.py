from werkzeug.security import generate_password_hash


TEST_PASSWORD = "Password123!"


def log_in(client, repository, email="tester@example.com"):
    """Create ``email`` if needed, log in through the real form, return its id."""

    user = repository.get_user_by_email(email)

    if user is None:
        user = repository.create_user(
            email,
            generate_password_hash(TEST_PASSWORD),
        )

    response = client.post(
        "/auth/login",
        data={"email": email, "password": TEST_PASSWORD},
    )

    assert response.status_code == 302, response.get_data(as_text=True)

    return user["id"]

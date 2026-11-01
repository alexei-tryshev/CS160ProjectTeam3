"""Login checks shared by every blueprint that shows or changes user data."""

from flask import jsonify, redirect, request, session, url_for


def current_user_id():
    """Return the logged-in user's id, or None when nobody is logged in."""

    return session.get("user_id")


def require_login():
    """``before_request`` hook for HTML pages.

    Sends logged-out visitors to the login page, remembering where they
    were headed so login can bring them back.
    """

    if current_user_id() is not None:
        return None

    target = request.full_path if request.query_string else request.path

    return redirect(url_for("auth.login", next=target))


def require_login_json():
    """``before_request`` hook for JSON endpoints: answer 401 instead."""

    if current_user_id() is not None:
        return None

    return jsonify({"error": "Log in to use this endpoint."}), 401


def safe_next_path(value):
    """Return ``value`` if it is a same-site path, otherwise None.

    Guards the post-login redirect so ``?next=`` cannot send users to
    another website.
    """

    if not isinstance(value, str):
        return None

    if not value.startswith("/") or value.startswith("//"):
        return None

    if "\\" in value:
        return None

    return value

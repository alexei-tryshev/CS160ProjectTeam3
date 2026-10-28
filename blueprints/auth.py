
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)


auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/auth",
)

MIN_PASSWORD_LENGTH = 8


def _repository():
    return current_app.extensions["repository"]


def _valid_email_format(email):
    if not isinstance(email, str):
        return False

    email = email.strip()

    if not email:
        return False

    if email.count("@") != 1:
        return False

    if " " in email:
        return False

    local_part, domain = email.rsplit("@", 1)

    return bool(
        local_part
        and domain
        and "." in domain
    )


def _validate_registration_form(form):
    email = str(
        form.get("email", "")
    ).strip().lower()

    password = str(
        form.get("password", "")
    )

    confirm_password = str(
        form.get("confirm_password", "")
    )

    errors = []

    if not email:
        errors.append("Email is required.")
    elif not _valid_email_format(email):
        errors.append("Enter a valid email address.")

    if not password:
        errors.append("Password is required.")
    elif len(password) < MIN_PASSWORD_LENGTH:
        errors.append(
            "Password must be at least {} characters long.".format(
                MIN_PASSWORD_LENGTH
            )
        )

    if password != confirm_password:
        errors.append("Passwords do not match.")

    return email, password, errors


def _is_duplicate_key_error(error):

    try:
        from pymongo.errors import DuplicateKeyError
    except ImportError:
        return False

    return isinstance(error, DuplicateKeyError)


@auth_bp.route(
    "/register",
    methods=["GET", "POST"],
)
def register():
    form = {
        "email": "",
    }

    errors = []
    status = 200

    if request.method == "POST":
        submitted_form = request.form.to_dict()

        email, password, errors = (
            _validate_registration_form(
                submitted_form
            )
        )
        form = {
            "email": email,
        }

        if not errors:
            repository = _repository()

            existing_user = (
                repository.get_user_by_email(email)
            )

            if existing_user is not None:
                errors.append(
                    "An account with that email already exists."
                )
            else:
                password_hash = generate_password_hash(
                    password
                )

                try:
                    repository.create_user(
                        email,
                        password_hash,
                    )
                except ValueError as exc:
                    errors.append(str(exc))
                except Exception as exc:
                    if _is_duplicate_key_error(exc):
                        errors.append(
                            "An account with that email already exists."
                        )
                    else:
                        raise
                else:
                    flash(
                        "Account created successfully. Please log in.",
                        "success",
                    )

                    return redirect(
                        url_for("auth.login")
                    )

        if errors:
            status = 400

    return (
        render_template(
            "register.html",
            form=form,
            errors=errors,
        ),
        status,
    )


@auth_bp.route(
    "/login",
    methods=["GET", "POST"],
)
def login():
    form = {
        "email": "",
    }

    errors = []
    status = 200

    if request.method == "POST":
        email = str(
            request.form.get("email", "")
        ).strip().lower()

        password = str(
            request.form.get("password", "")
        )

        form = {
            "email": email,
        }

        if not email or not password:
            errors.append(
                "Email and password are required."
            )
        elif not _valid_email_format(email):
            errors.append(
                "Enter a valid email address."
            )
        else:
            user = _repository().get_user_by_email(
                email
            )

            valid_credentials = False

            if user is not None:
                stored_password_hash = user.get(
                    "password_hash"
                )

                if (
                    isinstance(
                        stored_password_hash,
                        str,
                    )
                    and stored_password_hash
                ):
                    try:
                        valid_credentials = (
                            check_password_hash(
                                stored_password_hash,
                                password,
                            )
                        )
                    except (
                        TypeError,
                        ValueError,
                    ):
                        valid_credentials = False

            if not valid_credentials:

                errors.append(
                    "Invalid email or password."
                )
            else:
                session.clear()

                session["user_id"] = user["id"]
                session["email"] = user["email"]

                flash(
                    "Logged in successfully.",
                    "success",
                )

                return redirect(
                    url_for("main.home")
                )

        if errors:
            status = 400

    return (
        render_template(
            "login.html",
            form=form,
            errors=errors,
        ),
        status,
    )


@auth_bp.post("/logout")
def logout():
    session.clear()

    flash(
        "You have been logged out.",
        "success",
    )

    return redirect(
        url_for("main.home")
    )
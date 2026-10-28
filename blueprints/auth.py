
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.security import generate_password_hash


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

    email = str(form.get("email", "")).strip().lower()
    password = str(form.get("password", ""))
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
        form = request.form.to_dict()

        email, password, errors = (
            _validate_registration_form(form)
        )

        form["email"] = email

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
                        "Account created successfully.",
                        "success",
                    )

                    return redirect(
                        url_for("auth.register")
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
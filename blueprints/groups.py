"""Step-competition groups: create, join, leave, and the leaderboard."""

from datetime import date, datetime, timezone

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from blueprints.access import current_user_id, require_login
from groups import JOIN_FAILURE_WINDOW, MAX_JOIN_FAILURES
from summaries import PERIODS, leaderboard_rows, period_start
from validation import validate_display_name, validate_group_name


groups_bp = Blueprint("groups", __name__)
groups_bp.before_request(require_login)

PERIOD_LABELS = {
    "today": "Today",
    "week": "Week",
    "month": "Month",
}

DEFAULT_PERIOD = "today"

# Reachable before the user has chosen a display name.
NAME_SETUP_ENDPOINTS = {"groups.page", "groups.set_display_name"}


def _repository():
    return current_app.extensions["repository"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _current_user():
    return _repository().get_user(current_user_id())


def _has_display_name(user) -> bool:
    return bool(user and user.get("display_name"))


@groups_bp.before_request
def require_display_name():
    """Group members are shown by display name, so one must exist first."""

    if current_user_id() is None or request.endpoint in NAME_SETUP_ENDPOINTS:
        return None

    if not _has_display_name(_current_user()):
        return redirect(url_for("groups.page"))

    return None


def _member_group_or_404(group_id: str):
    """Return the group only if the logged-in user belongs to it.

    A group the user is not in looks exactly like one that does not
    exist, so group ids cannot be probed.
    """

    group = _repository().get_group(group_id)

    if group is None or current_user_id() not in group["member_ids"]:
        abort(404)

    return group


@groups_bp.get("/groups")
def page():
    user = _current_user()

    if user is None:
        session.clear()
        return redirect(url_for("auth.login"))

    if not _has_display_name(user):
        return render_template(
            "display_name.html",
            form={},
            errors=[],
        )

    groups = _repository().list_groups_for_user(user["id"])
    group_id = request.args.get("group", "").strip()

    # A blank ?group= means "no choice made", same as leaving it out.
    if group_id:
        selected = _member_group_or_404(group_id)
    else:
        selected = groups[0] if groups else None

    period = request.args.get("period", DEFAULT_PERIOD)

    if period not in PERIODS:
        period = DEFAULT_PERIOD

    rows = []

    if selected is not None:
        today = date.today()
        start = period_start(period, today).isoformat()
        end = today.isoformat()
        member_ids = selected["member_ids"]

        rows = leaderboard_rows(
            _repository().list_member_profiles(member_ids),
            _repository().list_entries_for_users_in_range(
                "steps",
                member_ids,
                start,
                end,
            ),
            start,
            end,
            user["id"],
        )

    return render_template(
        "groups.html",
        groups=groups,
        selected=selected,
        period=period,
        period_labels=PERIOD_LABELS,
        rows=rows,
    )


@groups_bp.post("/groups/display-name")
def set_display_name():
    user = _current_user()

    if user is None:
        session.clear()
        return redirect(url_for("auth.login"))

    # Changing an existing name is not offered yet.
    if _has_display_name(user):
        return redirect(url_for("groups.page"))

    display_name, errors = validate_display_name(request.form.to_dict())

    if not errors:
        try:
            _repository().update_user(
                user["id"],
                {"display_name": display_name},
            )
        except ValueError as exc:
            errors = [str(exc)]

    if errors:
        return render_template(
            "display_name.html",
            form={"display_name": display_name},
            errors=errors,
        ), 400

    flash("Display name saved.", "success")

    return redirect(url_for("groups.page"))


@groups_bp.post("/groups")
def create():
    name, errors = validate_group_name(request.form.to_dict())

    if errors:
        for error in errors:
            flash(error, "error")

        return redirect(url_for("groups.page"))

    try:
        group = _repository().create_group(name, current_user_id())
    except (ValueError, RuntimeError):
        flash("Could not create the group. Please try again.", "error")

        return redirect(url_for("groups.page"))

    flash(
        "Group created. Share the code {}.".format(group["join_code"]),
        "success",
    )

    return redirect(url_for("groups.page", group=group["id"]))


@groups_bp.post("/groups/join")
def join():
    now = _now()
    user_id = current_user_id()

    # Checked before looking at the code, so a correct guess made while
    # the limit applies is refused like any other.
    recent_failures = _repository().count_join_failures_since(
        user_id,
        now - JOIN_FAILURE_WINDOW,
    )

    if recent_failures >= MAX_JOIN_FAILURES:
        flash("Too many wrong codes. Try again in a few minutes.", "error")

        return redirect(url_for("groups.page"))

    group = _repository().get_group_by_code(request.form.get("code", ""))

    result = (
        "not_found"
        if group is None
        else _repository().add_group_member(group["id"], user_id)
    )

    if result == "not_found":
        _repository().record_join_failure(user_id, now)
        flash("No group has that code.", "error")

        return redirect(url_for("groups.page"))

    if result == "full":
        flash("That group is full.", "error")

        return redirect(url_for("groups.page"))

    if result == "already_member":
        flash("You're already in {}.".format(group["name"]), "success")
    else:
        flash("You joined {}.".format(group["name"]), "success")

    return redirect(url_for("groups.page", group=group["id"]))


@groups_bp.post("/groups/<group_id>/leave")
def leave(group_id: str):
    group = _member_group_or_404(group_id)

    if not _repository().remove_group_member(group["id"], current_user_id()):
        abort(404)

    flash("You left {}.".format(group["name"]), "success")

    return redirect(url_for("groups.page"))

from datetime import date

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from blueprints.entry_actions import (
    delete_entry_and_flash,
    entry_form_values,
    load_entry_for_edit,
    repository,
    save_entry_form,
)
from features import DEFAULT_USER_ID, DEFAULT_WATER_GOAL_OZ
from summaries import (
    daily_totals,
    goal_percent,
    total_for_date,
    window_start,
)
from validation import validate_goal


water_bp = Blueprint("water", __name__)


@water_bp.route(
    "/water",
    methods=["GET", "POST"],
)
def page():
    errors = []
    status = 200

    if request.method == "POST":
        form = request.form.to_dict()
        errors = save_entry_form("water", form)

        if not errors:
            return redirect(url_for("water.page"))

        status = 400
    else:
        form = {"date": date.today().isoformat()}
        edit_id = request.args.get("edit")

        if edit_id:
            entry = load_entry_for_edit("water", edit_id)

            if entry is None:
                errors = ["Entry not found."]
                status = 404
            else:
                form = entry_form_values(entry)

    today = date.today()

    week_entries = repository().list_entries_in_range(
        "water",
        DEFAULT_USER_ID,
        window_start(7, today),
        today.isoformat(),
    )

    goal_oz = (
        repository().get_water_goal(DEFAULT_USER_ID)
        or DEFAULT_WATER_GOAL_OZ
    )
    today_total = total_for_date(week_entries, today.isoformat())
    percent = goal_percent(today_total, goal_oz)

    entries = repository().list_entries(
        "water",
        DEFAULT_USER_ID,
    )

    return render_template(
        "water.html",
        form=form,
        errors=errors,
        editing=bool(form.get("entry_id")),
        entries=entries,
        today_total=today_total,
        goal_oz=goal_oz,
        percent=percent,
        bar_percent=min(percent, 100),
        chart=daily_totals(week_entries, today),
    ), status


@water_bp.post("/water/entries/<entry_id>/delete")
def delete(entry_id: str):
    delete_entry_and_flash("water", entry_id)

    return redirect(url_for("water.page"))


@water_bp.post("/water/goal")
def goal():
    goal_oz, errors = validate_goal(request.form.to_dict())

    for error in errors:
        flash(error, "error")

    if not errors:
        try:
            repository().set_water_goal(DEFAULT_USER_ID, goal_oz)
        except ValueError as exc:
            flash(str(exc), "error")
        else:
            flash("Daily goal updated.", "success")

    return redirect(url_for("water.page"))

from datetime import date

from flask import (
    Blueprint,
    redirect,
    render_template,
    request,
    url_for,
)

from blueprints.access import current_user_id, require_login
from blueprints.entry_actions import (
    delete_entry_and_flash,
    entry_form_values,
    load_entry_for_edit,
    repository,
    save_entry_form,
)
from summaries import (
    daily_step_totals,
    period_start,
    steps_total,
    window_start,
)


steps_bp = Blueprint("steps", __name__)
steps_bp.before_request(require_login)

RANGE_DAYS = {
    "1w": 7,
    "1m": 30,
}

RANGE_LABELS = {
    "1w": "1W",
    "1m": "1M",
}

DEFAULT_RANGE = "1w"


@steps_bp.route(
    "/steps",
    methods=["GET", "POST"],
)
def page():
    errors = []
    status = 200

    if request.method == "POST":
        form = request.form.to_dict()
        errors = save_entry_form("steps", form)

        if not errors:
            return redirect(url_for("steps.page"))

        status = 400
    else:
        form = {"date": date.today().isoformat()}
        edit_id = request.args.get("edit")

        if edit_id:
            entry = load_entry_for_edit("steps", edit_id)

            if entry is None:
                errors = ["Entry not found."]
                status = 404
            else:
                form = entry_form_values(entry)

    range_key = request.args.get("range", DEFAULT_RANGE)

    if range_key not in RANGE_DAYS:
        range_key = DEFAULT_RANGE

    today = date.today()
    today_iso = today.isoformat()
    days = RANGE_DAYS[range_key]
    week_start = period_start("week", today).isoformat()

    # One query covers both the chart window and the current week;
    # ending at today keeps future-dated entries out of the totals.
    window_entries = repository().list_entries_in_range(
        "steps",
        current_user_id(),
        min(window_start(days, today), week_start),
        today_iso,
    )

    entries = repository().list_entries(
        "steps",
        current_user_id(),
    )

    return render_template(
        "steps.html",
        form=form,
        errors=errors,
        editing=bool(form.get("entry_id")),
        entries=entries,
        today_total=steps_total(window_entries, today_iso, today_iso),
        week_total=steps_total(window_entries, week_start, today_iso),
        range_key=range_key,
        range_labels=RANGE_LABELS,
        range_days=days,
        chart=daily_step_totals(window_entries, today, days),
    ), status


@steps_bp.post("/steps/entries/<entry_id>/delete")
def delete(entry_id: str):
    delete_entry_and_flash("steps", entry_id)

    return redirect(url_for("steps.page"))

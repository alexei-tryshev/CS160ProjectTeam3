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
    calories_total,
    daily_calorie_totals,
    format_number,
    period_start,
    window_start,
)

nutrition_bp = Blueprint("nutrition", __name__)
nutrition_bp.before_request(require_login)

RANGE_DAYS = {
    "1w": 7,
    "1m": 30,
}
RANGE_LABELS = {
    "1w": "1W",
    "1m": "1M",
}
DEFAULT_RANGE = "1w"


@nutrition_bp.app_template_filter("nutrition_number")
def nutrition_number(value):
    return format_number(value)


@nutrition_bp.route(
    "/nutrition",
    methods=["GET", "POST"],
)
def page():
    errors = []
    status = 200
    if request.method == "POST":
        form = request.form.to_dict()
        errors = save_entry_form("nutrition", form)
        if not errors:
            return redirect(url_for("nutrition.page"))
        status = 400
    else:
        form = {"date": date.today().isoformat()}
        edit_id = request.args.get("edit")
        if edit_id:
            entry = load_entry_for_edit("nutrition", edit_id)
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
        "nutrition",
        current_user_id(),
        min(window_start(days, today), week_start),
        today_iso,
    )
    entries = repository().list_entries(
        "nutrition",
        current_user_id(),
    )
    return render_template(
        "nutrition.html",
        form=form,
        errors=errors,
        editing=bool(form.get("entry_id")),
        entries=entries,
        today_total=calories_total(window_entries, today_iso, today_iso),
        week_total=calories_total(window_entries, week_start, today_iso),
        range_key=range_key,
        range_labels=RANGE_LABELS,
        range_days=days,
        chart=daily_calorie_totals(window_entries, today, days),
    ), status


@nutrition_bp.post("/nutrition/entries/<entry_id>/delete")
def delete(entry_id: str):
    delete_entry_and_flash("nutrition", entry_id)
    return redirect(url_for("nutrition.page"))
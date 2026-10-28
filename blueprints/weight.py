from datetime import date

from flask import (
    Blueprint,
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
from features import DEFAULT_USER_ID
from summaries import (
    DEFAULT_RANGE,
    RANGE_DAYS,
    format_change,
    latest_weight,
    period_change,
    weight_changes,
    window_start,
)


weight_bp = Blueprint("weight", __name__)

RANGE_LABELS = {
    "1w": "1W",
    "1m": "1M",
    "3m": "3M",
    "all": "All",
}


@weight_bp.app_template_filter("signed_change")
def signed_change(value):
    return format_change(value)


@weight_bp.route(
    "/weight",
    methods=["GET", "POST"],
)
def page():
    errors = []
    status = 200

    if request.method == "POST":
        form = request.form.to_dict()
        errors = save_entry_form("weight", form)

        if not errors:
            return redirect(url_for("weight.page"))

        status = 400
    else:
        form = {"date": date.today().isoformat()}
        edit_id = request.args.get("edit")

        if edit_id:
            entry = load_entry_for_edit("weight", edit_id)

            if entry is None:
                errors = ["Entry not found."]
                status = 404
            else:
                form = entry_form_values(entry)

    range_key = request.args.get("range", DEFAULT_RANGE)

    if range_key not in RANGE_DAYS:
        range_key = DEFAULT_RANGE

    today = date.today()

    all_entries = repository().list_entries_in_range(
        "weight",
        DEFAULT_USER_ID,
    )

    start = window_start(RANGE_DAYS[range_key], today)
    window_entries = [
        entry
        for entry in all_entries
        if (start is None or entry["date"] >= start)
        and entry["date"] <= today.isoformat()
    ]

    entries = repository().list_entries(
        "weight",
        DEFAULT_USER_ID,
    )

    return render_template(
        "weight.html",
        form=form,
        errors=errors,
        editing=bool(form.get("entry_id")),
        entries=entries,
        changes=weight_changes(all_entries),
        latest=latest_weight(
            [
                entry
                for entry in all_entries
                if entry["date"] <= today.isoformat()
            ]
        ),
        period=period_change(window_entries),
        range_key=range_key,
        range_labels=RANGE_LABELS,
        chart=[
            {
                "date": entry["date"],
                "weight_lb": entry["data"]["weight_lb"],
            }
            for entry in window_entries
        ],
    ), status


@weight_bp.post("/weight/entries/<entry_id>/delete")
def delete(entry_id: str):
    delete_entry_and_flash("weight", entry_id)

    return redirect(url_for("weight.page"))

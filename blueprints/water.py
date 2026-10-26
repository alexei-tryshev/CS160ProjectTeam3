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
    ), status


@water_bp.post("/water/entries/<entry_id>/delete")
def delete(entry_id: str):
    delete_entry_and_flash("water", entry_id)

    return redirect(url_for("water.page"))

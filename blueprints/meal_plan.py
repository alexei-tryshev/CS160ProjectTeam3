from datetime import date

from flask import Blueprint, redirect, render_template, request, session, url_for

from blueprints.access import current_user_id, require_login
from blueprints.entry_actions import repository
from meal_plan import (
    ACTIVITY_LEVELS,
    GOALS,
    daily_targets,
    percent_of_target,
    remaining,
    suggest_meals,
    validate_plan,
)
from summaries import calories_total, macros_total

meal_plan_bp = Blueprint("meal_plan", __name__)
meal_plan_bp.before_request(require_login)

SESSION_KEY = "meal_plan"


def _latest_weight_lb():
    entries = repository().list_entries("weight", current_user_id(), limit=1)
    if entries:
        return entries[0]["data"].get("weight_lb")
    return None


@meal_plan_bp.route("/meal-plan", methods=["GET", "POST"])
def page():
    errors = []
    status = 200
    plan = session.get(SESSION_KEY)

    if request.method == "POST":
        form = request.form.to_dict()
        new_plan, errors = validate_plan(form)
        if not errors:
            session[SESSION_KEY] = new_plan
            return redirect(url_for("meal_plan.page"))
        status = 400
    elif plan and request.args.get("edit") is None:
        form = dict(plan)
    else:
        form = dict(plan or {})
        form.setdefault("weight_lb", _latest_weight_lb() or "")

    editing = plan is None or request.args.get("edit") is not None or bool(errors)

    targets = eaten = left = percents = None
    meals = []
    if plan and not editing:
        today = date.today().isoformat()
        entries = repository().list_entries_in_range(
            "nutrition", current_user_id(), today, today
        )
        eaten = dict(macros_total(entries, today, today))
        eaten["calories"] = calories_total(entries, today, today)
        targets = daily_targets(plan)
        left = remaining(targets, eaten)
        percents = percent_of_target(targets, eaten)
        meals = suggest_meals(left)

    return render_template(
        "meal_plan.html",
        form=form,
        errors=errors,
        editing=editing,
        plan=plan,
        goals=GOALS,
        activity_levels=ACTIVITY_LEVELS,
        targets=targets,
        eaten=eaten,
        left=left,
        percents=percents,
        meals=meals,
    ), status
from flask import Blueprint, render_template

from blueprints.access import require_login
from features import FEATURES


main_bp = Blueprint("main", __name__)
main_bp.before_request(require_login)


@main_bp.app_context_processor
def inject_features():
    """Make the shared feature configuration available to templates."""

    return {"features": FEATURES}


@main_bp.get("/")
def home():
    """Render the dashboard."""

    return render_template("index.html")

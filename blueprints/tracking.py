from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from features import (
    DEFAULT_USER_ID,
    FEATURES,
    normalize_feature,
)
from validation import validate_entry


tracking_bp = Blueprint(
    "tracking",
    __name__,
)


def _repository():
    return current_app.extensions["repository"]


@tracking_bp.route(
    "/<feature>",
    methods=["GET", "POST"],
)
def feature_page(feature: str):
    feature = normalize_feature(feature)

    if feature not in FEATURES:
        abort(404)

    form = (
        request.form.to_dict()
        if request.method == "POST"
        else {}
    )

    errors = []

    if request.method == "POST":
        payload, errors = validate_entry(
            feature,
            form,
        )

        if not errors:
            try:
                _repository().create_entry(
                    feature,
                    DEFAULT_USER_ID,
                    payload,
                )
            except ValueError as exc:
                errors = [str(exc)]
            else:
                flash(
                    "Entry saved.",
                    "success",
                )

                return redirect(
                    url_for(
                        "tracking.feature_page",
                        feature=feature,
                    )
                )

    entries = _repository().list_entries(
        feature,
        DEFAULT_USER_ID,
    )

    return render_template(
        "feature.html",
        feature=feature,
        config=FEATURES[feature],
        form=form,
        errors=errors,
        entries=entries,
    ), 400 if errors else 200
from flask import Blueprint, current_app, jsonify, request

from features import DEFAULT_USER_ID, FEATURES, normalize_feature
from validation import validate_entry


api_bp = Blueprint("api", __name__, url_prefix="/api")


def _repository():
    return current_app.extensions["repository"]


@api_bp.get("/health")
def health():
    """Return the application status and active repository backend."""

    return jsonify(
        {
            "status": "ok",
            "repository": current_app.config["REPOSITORY_BACKEND"],
        }
    )


@api_bp.route("/entries/<feature>", methods=["GET", "POST"])
def entries_api(feature: str):
    """List or create a validated entry for a tracking feature."""

    feature = normalize_feature(feature)
    if feature not in FEATURES:
        return jsonify({"error": "Unknown feature."}), 404

    if request.method == "GET":
        user_id = request.args.get("user_id", DEFAULT_USER_ID)
        entries = _repository().list_entries(feature, user_id)
        return jsonify({"feature": feature, "user_id": user_id, "entries": entries})

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400

    body = dict(body)
    user_id = str(body.pop("user_id", DEFAULT_USER_ID))
    payload, errors = validate_entry(feature, body)
    if errors:
        return jsonify({"errors": errors}), 400

    entry = _repository().add_entry(feature, user_id, payload)
    return jsonify({"entry": entry}), 201

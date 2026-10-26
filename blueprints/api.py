from flask import Blueprint, current_app, jsonify, request

from features import DEFAULT_USER_ID, FEATURES, normalize_feature
from validation import validate_entry


api_bp = Blueprint(
    "api",
    __name__,
    url_prefix="/api",
)


def _repository():
    return current_app.extensions["repository"]


def _user_id_from_value(value):
    if not isinstance(value, str) or not value.strip():
        return None

    return value.strip()


@api_bp.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "repository": current_app.config[
                "REPOSITORY_BACKEND"
            ],
        }
    )


@api_bp.route(
    "/entries/<feature>",
    methods=["GET", "POST"],
)
def entries_api(feature: str):

    feature = normalize_feature(feature)

    if feature not in FEATURES:
        return jsonify(
            {"error": "Unknown feature."}
        ), 404

    if request.method == "GET":
        user_id = _user_id_from_value(
            request.args.get(
                "user_id",
                DEFAULT_USER_ID,
            )
        )

        if user_id is None:
            return jsonify(
                {"error": "user_id is required."}
            ), 400

        entries = _repository().list_entries(
            feature,
            user_id,
        )

        return jsonify(
            {
                "feature": feature,
                "user_id": user_id,
                "entries": entries,
            }
        )

    body = request.get_json(silent=True)

    if not isinstance(body, dict):
        return jsonify(
            {
                "error": (
                    "Request body must be a JSON object."
                )
            }
        ), 400

    body = dict(body)

    user_id = _user_id_from_value(
        body.pop(
            "user_id",
            DEFAULT_USER_ID,
        )
    )

    if user_id is None:
        return jsonify(
            {"errors": ["user_id is required."]}
        ), 400

    payload, errors = validate_entry(
        feature,
        body,
    )

    if errors:
        return jsonify({"errors": errors}), 400

    try:
        entry = _repository().create_entry(
            feature,
            user_id,
            payload,
        )
    except ValueError as exc:
        return jsonify(
            {"errors": [str(exc)]}
        ), 400

    return jsonify({"entry": entry}), 201


@api_bp.route(
    "/entries/<feature>/<entry_id>",
    methods=["GET", "PUT", "DELETE"],
)
def entry_api(feature: str, entry_id: str):

    feature = normalize_feature(feature)

    if feature not in FEATURES:
        return jsonify(
            {"error": "Unknown feature."}
        ), 404

    if request.method == "GET":
        user_id = _user_id_from_value(
            request.args.get(
                "user_id",
                DEFAULT_USER_ID,
            )
        )

        if user_id is None:
            return jsonify(
                {"error": "user_id is required."}
            ), 400

        entry = _repository().get_entry(
            entry_id,
            feature,
            user_id,
        )

        if entry is None:
            return jsonify(
                {"error": "Entry not found."}
            ), 404

        return jsonify({"entry": entry})

    if request.method == "DELETE":
        user_id = _user_id_from_value(
            request.args.get(
                "user_id",
                DEFAULT_USER_ID,
            )
        )

        if user_id is None:
            return jsonify(
                {"error": "user_id is required."}
            ), 400

        deleted = _repository().delete_entry(
            entry_id,
            feature,
            user_id,
        )

        if not deleted:
            return jsonify(
                {"error": "Entry not found."}
            ), 404

        return jsonify({"deleted": True})

    body = request.get_json(silent=True)

    if not isinstance(body, dict):
        return jsonify(
            {
                "error": (
                    "Request body must be a JSON object."
                )
            }
        ), 400

    body = dict(body)

    user_id = _user_id_from_value(
        body.pop(
            "user_id",
            DEFAULT_USER_ID,
        )
    )

    if user_id is None:
        return jsonify(
            {"errors": ["user_id is required."]}
        ), 400

    payload, errors = validate_entry(
        feature,
        body,
    )

    if errors:
        return jsonify({"errors": errors}), 400

    try:
        entry = _repository().update_entry(
            entry_id,
            feature,
            user_id,
            payload,
        )
    except ValueError as exc:
        return jsonify(
            {"errors": [str(exc)]}
        ), 400

    if entry is None:
        return jsonify(
            {"error": "Entry not found."}
        ), 404

    return jsonify({"entry": entry})
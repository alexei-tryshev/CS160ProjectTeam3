from typing import Any, Dict, List, Tuple


USERS_COLLECTION = "users"
ENTRIES_COLLECTION = "entries"


FEATURE_PAYLOAD_FIELDS: Dict[str, Tuple[str, ...]] = {
    "nutrition": (
        "date",
        "food",
        "calories",
        "protein_g",
        "carbs_g",
        "fat_g",
    ),
    "water": (
        "date",
        "amount_ml",
    ),
    "steps": (
        "date",
        "steps",
    ),
    "weight": (
        "date",
        "weight_kg",
    ),
}


ENTRY_INDEXES: List[Dict[str, Any]] = [
    {
        "keys": [
            ("user_id", 1),
            ("feature", 1),
            ("date", -1),
        ],
        "name": "entries_by_user_feature_date",
    },
    {
        "keys": [
            ("user_id", 1),
            ("created_at", -1),
        ],
        "name": "entries_by_user_created_at",
    },
]


USER_INDEXES: List[Dict[str, Any]] = [
    {
        "keys": [("email", 1)],
        "name": "users_by_email",
        "unique": True,
    },
]


ENTRY_REQUIRED_FIELDS = (
    "feature",
    "user_id",
    "date",
    "data",
    "created_at",
)


def validate_entry_document_shape(
    document: Dict[str, Any],
) -> List[str]:

    errors: List[str] = []

    for field in ENTRY_REQUIRED_FIELDS:
        if field not in document:
            errors.append(
                "Missing top-level field: {}.".format(field)
            )

    feature = document.get("feature")

    if not isinstance(feature, str) or not feature:
        errors.append(
            "The feature field must be a non-empty string."
        )
    elif feature not in FEATURE_PAYLOAD_FIELDS:
        errors.append(
            "Unsupported feature: {}.".format(feature)
        )

    user_id = document.get("user_id")

    if not isinstance(user_id, str) or not user_id:
        errors.append(
            "The user_id field must be a non-empty string."
        )

    date = document.get("date")

    if not isinstance(date, str) or not date:
        errors.append(
            "The date field must be a non-empty string."
        )

    created_at = document.get("created_at")

    if not isinstance(created_at, str) or not created_at:
        errors.append(
            "The created_at field must be a non-empty string."
        )

    data = document.get("data")

    if not isinstance(data, dict):
        errors.append("The data field must be an object.")

    elif isinstance(feature, str) and feature in FEATURE_PAYLOAD_FIELDS:
        for field in FEATURE_PAYLOAD_FIELDS[feature]:
            if field not in data:
                errors.append(
                    "Missing data field: {}.".format(field)
                )

        if "date" in data and data["date"] != date:
            errors.append(
                "The top-level date must match data.date."
            )

    return errors
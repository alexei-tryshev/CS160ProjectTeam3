from datetime import date, datetime
import math
from typing import Any, Dict, List, Tuple


USERS_COLLECTION = "users"

# Largest integer BSON can store (signed 64-bit).
MAX_BSON_INT = 2 ** 63 - 1
ENTRIES_COLLECTION = "entries"
GOALS_COLLECTION = "goals"


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


GOAL_INDEXES: List[Dict[str, Any]] = [
    {
        "keys": [("user_id", 1)],
        "name": "goals_by_user",
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

USER_REQUIRED_FIELDS = (
    "email",
    "password_hash",
    "created_at",
)

GOAL_REQUIRED_FIELDS = (
    "user_id",
    "water_goal_ml",
    "updated_at",
)


def _valid_date(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False

    try:
        date.fromisoformat(value)
    except ValueError:
        return False

    return True


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False

    try:
        datetime.fromisoformat(value)
    except ValueError:
        return False

    return True


def _valid_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _valid_non_negative_number(value: Any) -> bool:
    return _valid_number(value) and value >= 0


def _valid_non_negative_integer(value: Any) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and 0 <= value <= MAX_BSON_INT
    )


def _valid_email(value: Any) -> bool:
    if not isinstance(value, str):
        return False

    email = value.strip()

    return (
        bool(email)
        and email.count("@") == 1
        and " " not in email
        and "." in email.rsplit("@", 1)[1]
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

    if not isinstance(user_id, str) or not user_id.strip():
        errors.append(
            "The user_id field must be a non-empty string."
        )

    top_level_date = document.get("date")

    if not _valid_date(top_level_date):
        errors.append(
            "The date field must use YYYY-MM-DD format."
        )

    created_at = document.get("created_at")

    if not _valid_timestamp(created_at):
        errors.append(
            "The created_at field must be an ISO-8601 timestamp."
        )

    data = document.get("data")

    if not isinstance(data, dict):
        errors.append("The data field must be an object.")
        return errors

    if not isinstance(feature, str) or feature not in FEATURE_PAYLOAD_FIELDS:
        return errors

    expected_fields = set(FEATURE_PAYLOAD_FIELDS[feature])
    actual_fields = set(data.keys())

    for field in sorted(expected_fields - actual_fields):
        errors.append(
            "Missing data field: {}.".format(field)
        )

    for field in sorted(actual_fields - expected_fields):
        errors.append(
            "Unknown data field: {}.".format(field)
        )

    nested_date = data.get("date")

    if not _valid_date(nested_date):
        errors.append(
            "The data.date field must use YYYY-MM-DD format."
        )
    elif nested_date != top_level_date:
        errors.append(
            "The top-level date must match data.date."
        )

    if feature == "nutrition":
        food = data.get("food")

        if not isinstance(food, str) or not food.strip():
            errors.append(
                "The data.food field must be non-empty text."
            )

        for field in (
            "calories",
            "protein_g",
            "carbs_g",
            "fat_g",
        ):
            if field in data and not _valid_non_negative_number(
                data[field]
            ):
                errors.append(
                    "The data.{} field must be a non-negative number.".format(
                        field
                    )
                )

    elif feature == "water":
        amount = data.get("amount_ml")

        if not _valid_non_negative_integer(amount):
            errors.append(
                "The data.amount_ml field must be a non-negative integer."
            )

    elif feature == "steps":
        steps = data.get("steps")

        if not _valid_non_negative_integer(steps):
            errors.append(
                "The data.steps field must be a non-negative integer."
            )

    elif feature == "weight":
        weight = data.get("weight_kg")

        if not _valid_number(weight) or weight <= 0:
            errors.append(
                "The data.weight_kg field must be greater than zero."
            )

    return errors


def validate_user_document_shape(
    document: Dict[str, Any],
) -> List[str]:

    errors: List[str] = []

    for field in USER_REQUIRED_FIELDS:
        if field not in document:
            errors.append(
                "Missing user field: {}.".format(field)
            )

    if not _valid_email(document.get("email")):
        errors.append(
            "The email field must contain a valid email address."
        )

    password_hash = document.get("password_hash")

    if not isinstance(password_hash, str) or not password_hash.strip():
        errors.append(
            "The password_hash field must be non-empty text."
        )

    if "password" in document:
        errors.append(
            "Store password_hash instead of a plain-text password."
        )

    if not _valid_timestamp(document.get("created_at")):
        errors.append(
            "The user created_at field must be an ISO-8601 timestamp."
        )

    return errors


def validate_goal_document_shape(
    document: Dict[str, Any],
) -> List[str]:

    errors: List[str] = []

    for field in GOAL_REQUIRED_FIELDS:
        if field not in document:
            errors.append(
                "Missing goal field: {}.".format(field)
            )

    user_id = document.get("user_id")

    if not isinstance(user_id, str) or not user_id.strip():
        errors.append(
            "The user_id field must be a non-empty string."
        )

    water_goal_ml = document.get("water_goal_ml")

    if not _valid_non_negative_integer(water_goal_ml) or water_goal_ml == 0:
        errors.append(
            "The water_goal_ml field must be a whole number greater than zero."
        )

    if not _valid_timestamp(document.get("updated_at")):
        errors.append(
            "The goal updated_at field must be an ISO-8601 timestamp."
        )

    return errors

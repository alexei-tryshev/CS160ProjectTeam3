from datetime import date
from typing import Any, Dict, List, Optional, Tuple


def _text(raw: Dict[str, Any], name: str) -> str:
    value = raw.get(name, "")
    return str(value).strip()


def _decimal(
    raw: Dict[str, Any],
    name: str,
    label: str,
    errors: List[str],
    minimum: Optional[float] = None,
) -> float:
    value = _text(raw, name)

    if not value:
        errors.append("{} is required.".format(label))
        return 0.0

    try:
        number = float(value)
    except (TypeError, ValueError):
        errors.append("{} must be a number.".format(label))
        return 0.0

    if minimum is not None and number <= minimum:
        errors.append("{} must be greater than {}.".format(label, minimum))
    elif number < 0:
        errors.append("{} cannot be negative.".format(label))

    return number


MAX_WATER_AMOUNT_OZ = 350
MAX_WATER_GOAL_OZ = 700


def _whole_number(
    raw: Dict[str, Any],
    name: str,
    label: str,
    errors: List[str],
    maximum: Optional[int] = None,
    unit: str = "",
) -> int:
    value = _text(raw, name)

    if not value:
        errors.append("{} is required.".format(label))
        return 0

    try:
        number = int(value)
    except (TypeError, ValueError):
        errors.append("{} must be a whole number.".format(label))
        return 0

    if number < 0:
        errors.append("{} cannot be negative.".format(label))
    elif maximum is not None and number > maximum:
        errors.append(
            "{} must be at most {:,}{}.".format(label, maximum, unit)
        )

    return number


def _date(raw: Dict[str, Any], errors: List[str]) -> str:
    value = _text(raw, "date") or date.today().isoformat()

    try:
        # Normalize accepted variants such as 20261024 so stored dates
        # always sort and compare as YYYY-MM-DD strings.
        return date.fromisoformat(value).isoformat()
    except ValueError:
        errors.append("Date must use YYYY-MM-DD format.")

    return value


def validate_entry(
    feature: str,
    raw: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[str]]:
    """Return a typed payload and user-readable validation errors."""

    errors: List[str] = []
    payload: Dict[str, Any] = {
        "date": _date(raw, errors)
    }

    if feature == "nutrition":
        food = _text(raw, "food")

        if not food:
            errors.append("Food is required.")

        payload.update(
            {
                "food": food,
                "calories": _decimal(
                    raw, "calories", "Calories", errors
                ),
                "protein_g": _decimal(
                    raw, "protein_g", "Protein", errors
                ),
                "carbs_g": _decimal(
                    raw, "carbs_g", "Carbohydrates", errors
                ),
                "fat_g": _decimal(
                    raw, "fat_g", "Fat", errors
                ),
            }
        )

    elif feature == "water":
        payload["amount_oz"] = _whole_number(
            raw,
            "amount_oz",
            "Amount",
            errors,
            maximum=MAX_WATER_AMOUNT_OZ,
            unit=" fl oz",
        )

    elif feature == "steps":
        payload["steps"] = _whole_number(
            raw, "steps", "Steps", errors
        )

    elif feature == "weight":
        payload["weight_lb"] = _decimal(
            raw,
            "weight_lb",
            "Weight",
            errors,
            minimum=0.0,
        )

    else:
        errors.append("Unknown feature.")

    return payload, errors

def validate_goal(
    raw: Dict[str, Any],
) -> Tuple[Optional[int], List[str]]:
    """Return the daily water goal in fl oz and user-readable errors."""

    value = _text(raw, "water_goal_oz")

    try:
        goal = int(value)
    except ValueError:
        goal = 0

    if goal <= 0:
        return None, [
            "Daily goal must be a whole number greater than zero."
        ]

    if goal > MAX_WATER_GOAL_OZ:
        return None, [
            "Daily goal must be at most {:,} fl oz.".format(MAX_WATER_GOAL_OZ)
        ]

    return goal, []

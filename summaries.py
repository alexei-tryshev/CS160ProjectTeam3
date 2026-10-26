from datetime import date, timedelta
from typing import Any, Dict, List, Optional


RANGE_DAYS: Dict[str, Optional[int]] = {
    "1w": 7,
    "1m": 30,
    "3m": 90,
    "all": None,
}

DEFAULT_RANGE = "1w"


def _chronological(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        entries,
        key=lambda entry: (
            entry["date"],
            entry["created_at"],
        ),
    )


def window_start(days: Optional[int], today: date) -> Optional[str]:
    if days is None:
        return None

    return (today - timedelta(days=days - 1)).isoformat()


def total_for_date(entries: List[Dict[str, Any]], day: str) -> int:
    return sum(
        entry["data"]["amount_ml"]
        for entry in entries
        if entry["date"] == day
    )


def daily_totals(
    entries: List[Dict[str, Any]],
    today: date,
    days: int = 7,
) -> List[Dict[str, Any]]:
    """Return one total per day, oldest first, ending today."""

    return [
        {
            "date": day,
            "total_ml": total_for_date(entries, day),
        }
        for day in (
            (today - timedelta(days=offset)).isoformat()
            for offset in range(days - 1, -1, -1)
        )
    ]


def goal_percent(total_ml: int, goal_ml: int) -> int:
    return round(100 * total_ml / goal_ml)


def weight_changes(
    entries: List[Dict[str, Any]],
) -> Dict[str, Optional[float]]:
    """Map each entry id to its change from the previous entry."""

    changes: Dict[str, Optional[float]] = {}
    previous = None

    for entry in _chronological(entries):
        weight = entry["data"]["weight_kg"]
        changes[entry["id"]] = (
            None if previous is None else round(weight - previous, 1)
        )
        previous = weight

    return changes


def latest_weight(entries: List[Dict[str, Any]]) -> Optional[float]:
    if not entries:
        return None

    return _chronological(entries)[-1]["data"]["weight_kg"]


def period_change(entries: List[Dict[str, Any]]) -> Optional[float]:
    if len(entries) < 2:
        return None

    ordered = _chronological(entries)

    return round(
        ordered[-1]["data"]["weight_kg"] - ordered[0]["data"]["weight_kg"],
        1,
    )


def format_change(value: Optional[float]) -> str:
    if value is None:
        return "—"

    if value == 0:
        return "0.0"

    if value < 0:
        return "−{:.1f}".format(-value)

    return "+{:.1f}".format(value)

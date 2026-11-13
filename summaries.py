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
        entry["data"]["amount_oz"]
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
            "total_oz": total_for_date(entries, day),
        }
        for day in (
            (today - timedelta(days=offset)).isoformat()
            for offset in range(days - 1, -1, -1)
        )
    ]


def goal_percent(total_oz: int, goal_oz: int) -> int:
    return round(100 * total_oz / goal_oz)


PERIODS = ("today", "week", "month")


def steps_total(
    entries: List[Dict[str, Any]],
    start: str,
    end: str,
) -> int:
    """Sum steps for entries dated from ``start`` to ``end`` inclusive."""
    return sum(
        entry["data"]["steps"]
        for entry in entries
        if start <= entry["date"] <= end
    )


def daily_step_totals(
    entries: List[Dict[str, Any]],
    today: date,
    days: int,
) -> List[Dict[str, Any]]:
    """Return one steps total per day, oldest first, ending today."""
    return [
        {
            "date": day,
            "total_steps": steps_total(entries, day, day),
        }
        for day in (
            (today - timedelta(days=offset)).isoformat()
            for offset in range(days - 1, -1, -1)
        )
    ]


MACRO_FIELDS = ("protein_g", "carbs_g", "fat_g")


def calories_total(
    entries: List[Dict[str, Any]],
    start: str,
    end: str,
) -> float:
    """Sum calories for entries dated from ``start`` to ``end`` inclusive."""
    return round(
        sum(
            entry["data"]["calories"]
            for entry in entries
            if start <= entry["date"] <= end
        ),
        1,
    )


def daily_calorie_totals(
    entries: List[Dict[str, Any]],
    today: date,
    days: int = 7,
) -> List[Dict[str, Any]]:
    """Return one calorie total per day, oldest first, ending today."""
    return [
        {
            "date": day,
            "total_calories": calories_total(entries, day, day),
        }
        for day in (
            (today - timedelta(days=offset)).isoformat()
            for offset in range(days - 1, -1, -1)
        )
    ]


def macros_total(
    entries: List[Dict[str, Any]],
    start: str,
    end: str,
) -> Dict[str, float]:
    """Sum protein, carbs, and fat (g) from ``start`` to ``end`` inclusive."""
    in_range = [
        entry
        for entry in entries
        if start <= entry["date"] <= end
    ]
    return {
        field: round(
            sum(entry["data"][field] for entry in in_range),
            1,
        )
        for field in MACRO_FIELDS
    }


def macro_percentages(
    totals: Dict[str, float],
) -> Dict[str, int]:
    """Return each macronutrient's share (0-100) of total macronutrient grams."""
    total_grams = sum(totals.get(field, 0.0) for field in MACRO_FIELDS)
    if total_grams <= 0:
        return {field: 0 for field in MACRO_FIELDS}
    return {
        field: round(100 * totals.get(field, 0.0) / total_grams)
        for field in MACRO_FIELDS
    }


def daily_macro_totals(
    entries: List[Dict[str, Any]],
    today: date,
    days: int = 7,
) -> List[Dict[str, Any]]:
    """Return daily protein, carbs, and fat totals, oldest first, ending today."""
    rows: List[Dict[str, Any]] = []
    for offset in range(days - 1, -1, -1):
        day = (today - timedelta(days=offset)).isoformat()
        totals = macros_total(entries, day, day)
        rows.append(
            {
                "date": day,
                "protein_g": totals["protein_g"],
                "carbs_g": totals["carbs_g"],
                "fat_g": totals["fat_g"],
            }
        )
    return rows


def format_number(value: float) -> str:
    """Format a numeric value without trailing .0 when it is a whole number."""
    rounded = round(float(value), 1)
    if rounded.is_integer():
        return "{:,}".format(int(rounded))
    return "{:,.1f}".format(rounded)


def period_start(period: str, today: date) -> date:
    """First day of a leaderboard period: weeks start Monday, months on the 1st."""
    if period == "today":
        return today
    if period == "week":
        return today - timedelta(days=today.weekday())
    if period == "month":
        return today.replace(day=1)
    raise ValueError("Unknown period: {}.".format(period))


def leaderboard_rows(
    members: List[Dict[str, Any]],
    entries: List[Dict[str, Any]],
    start: str,
    end: str,
    viewer_id: str,
) -> List[Dict[str, Any]]:
    """Rank group members by steps from ``start`` to ``end`` inclusive.

    Every member gets a row, even with no steps. Equal totals share a
    rank and the next rank skips (1, 1, 3). Rows carry only a name and
    a total, never an email or individual entries.
    """
    totals = {member["id"]: 0 for member in members}
    for entry in entries:
        if entry["user_id"] in totals and start <= entry["date"] <= end:
            totals[entry["user_id"]] += entry["data"]["steps"]

    rows = [
        {
            "user_id": member["id"],
            "name": member.get("display_name") or "Member",
            "steps": totals[member["id"]],
            "is_you": member["id"] == viewer_id,
        }
        for member in members
    ]
    rows.sort(key=lambda row: (-row["steps"], row["name"].lower()))

    for position, row in enumerate(rows):
        tied_with_previous = (
            position > 0 and rows[position - 1]["steps"] == row["steps"]
        )
        row["rank"] = (
            rows[position - 1]["rank"] if tied_with_previous else position + 1
        )
    return rows


def weight_changes(
    entries: List[Dict[str, Any]],
) -> Dict[str, Optional[float]]:
    """Map each entry id to its change from the previous entry."""
    changes: Dict[str, Optional[float]] = {}
    previous = None
    for entry in _chronological(entries):
        weight = entry["data"]["weight_lb"]
        changes[entry["id"]] = (
            None if previous is None else round(weight - previous, 1)
        )
        previous = weight
    return changes


def latest_weight(entries: List[Dict[str, Any]]) -> Optional[float]:
    if not entries:
        return None
    return _chronological(entries)[-1]["data"]["weight_lb"]


def period_change(entries: List[Dict[str, Any]]) -> Optional[float]:
    if len(entries) < 2:
        return None
    ordered = _chronological(entries)
    return round(
        ordered[-1]["data"]["weight_lb"] - ordered[0]["data"]["weight_lb"],
        1,
    )


def format_change(value: Optional[float]) -> str:
    if value is None:
        return "\u2014"
    if value == 0:
        return "0.0"
    if value < 0:
        return "\u2212{:.1f}".format(-value)
    return "+{:.1f}".format(value)
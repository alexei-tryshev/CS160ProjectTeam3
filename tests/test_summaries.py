import unittest
from datetime import date

from summaries import (
    daily_totals,
    format_change,
    goal_percent,
    latest_weight,
    period_change,
    weight_changes,
    window_start,
)
from validation import validate_entry, validate_goal


def e(entry_id, entry_date, created_at="2026-10-01T00:00:00+00:00", **data):
    return {
        "id": entry_id,
        "date": entry_date,
        "created_at": created_at,
        "data": dict(data, date=entry_date),
    }


class SummaryTestCase(unittest.TestCase):

    def test_daily_totals_zero_fills_seven_days_ending_today(self):
        entries = [
            e("a", "2026-10-25", amount_oz=16),
            e("b", "2026-10-25", amount_oz=8),
            e("c", "2026-10-20", amount_oz=32),
            e("d", "2026-10-18", amount_oz=9),
            e("f", "2026-10-26", amount_oz=9),
        ]

        totals = daily_totals(entries, date(2026, 10, 25))

        self.assertEqual(totals[0]["date"], "2026-10-19")
        self.assertEqual(len(totals), 7)
        self.assertEqual(totals[-1], {"date": "2026-10-25", "total_oz": 24})
        self.assertEqual(totals[1], {"date": "2026-10-20", "total_oz": 32})
        self.assertEqual(sum(t["total_oz"] for t in totals), 56)

    def test_goal_percent_can_exceed_one_hundred(self):
        self.assertEqual(goal_percent(56, 80), 70)
        self.assertEqual(goal_percent(96, 64), 150)
        self.assertEqual(goal_percent(0, 64), 0)

    def test_window_start(self):
        self.assertEqual(window_start(7, date(2026, 10, 25)), "2026-10-19")
        self.assertEqual(window_start(30, date(2026, 10, 25)), "2026-09-26")
        self.assertIsNone(window_start(None, date(2026, 10, 25)))

    def test_weight_changes_rounds_float_noise_and_orders_by_date_then_created(self):
        entries = [
            e("c", "2026-10-25", weight_lb=168.5),
            e("a", "2026-10-20", weight_lb=169.3),
            e("b", "2026-10-22", weight_lb=168.8),
        ]

        self.assertEqual(weight_changes(entries), {"a": None, "b": -0.5, "c": -0.3})

        same_day = [
            e("x", "2026-10-25", "2026-10-25T08:00:00+00:00", weight_lb=170.0),
            e("y", "2026-10-25", "2026-10-25T20:00:00+00:00", weight_lb=170.4),
        ]

        self.assertEqual(weight_changes(same_day)["y"], 0.4)

    def test_latest_and_period_change(self):
        entries = [
            e("a", "2026-10-20", weight_lb=169.3),
            e("c", "2026-10-25", weight_lb=168.5),
        ]

        self.assertEqual(latest_weight(entries), 168.5)
        self.assertEqual(period_change(entries), -0.8)
        self.assertIsNone(period_change(entries[:1]))
        self.assertIsNone(latest_weight([]))

    def test_format_change(self):
        self.assertEqual(format_change(None), "—")
        self.assertEqual(format_change(0.3), "+0.3")
        self.assertEqual(format_change(-0.8), "−0.8")
        self.assertEqual(format_change(0.0), "0.0")

    def test_validate_goal(self):
        self.assertEqual(validate_goal({"water_goal_oz": " 80 "}), (80, []))

        for bad in ("", "0", "-5", "2.5", "abc"):
            goal, errors = validate_goal({"water_goal_oz": bad})
            self.assertIsNone(goal)
            self.assertEqual(
                errors,
                ["Daily goal must be a whole number greater than zero."],
            )

    def test_validate_entry_normalizes_compact_iso_dates(self):
        payload, errors = validate_entry("water", {"date": "20261024", "amount_oz": "1"})

        self.assertEqual(errors, [])
        self.assertEqual(payload["date"], "2026-10-24")


if __name__ == "__main__":
    unittest.main()

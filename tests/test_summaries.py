import unittest
from datetime import date

from summaries import (
    daily_step_totals,
    daily_totals,
    format_change,
    goal_percent,
    latest_weight,
    leaderboard_rows,
    period_change,
    period_start,
    steps_total,
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


def steps(entry_date, count):
    return e("s", entry_date, steps=count)


class StepsSummaryTestCase(unittest.TestCase):

    def test_steps_total_sums_inclusive_range_and_ignores_outside(self):
        entries = [
            steps("2026-11-08", 4444),
            steps("2026-11-09", 1000),
            steps("2026-11-12", 2000),
            steps("2026-11-12", 500),
            steps("2026-11-13", 9999),
        ]

        self.assertEqual(steps_total(entries, "2026-11-09", "2026-11-12"), 3500)

    def test_daily_step_totals_fills_missing_days_with_zero(self):
        rows = daily_step_totals(
            [steps("2026-11-12", 700), steps("2026-11-12", 50)],
            date(2026, 11, 12),
            7,
        )

        self.assertEqual(len(rows), 7)
        self.assertEqual(rows[0], {"date": "2026-11-06", "total_steps": 0})
        self.assertEqual(rows[-1], {"date": "2026-11-12", "total_steps": 750})

    def test_period_start(self):
        thursday = date(2026, 11, 12)

        self.assertEqual(period_start("today", thursday), thursday)
        self.assertEqual(period_start("week", thursday), date(2026, 11, 9))
        self.assertEqual(period_start("month", thursday), date(2026, 11, 1))
        self.assertEqual(period_start("week", date(2026, 11, 9)), date(2026, 11, 9))
        self.assertEqual(period_start("week", date(2026, 12, 2)), date(2026, 11, 30))
        self.assertEqual(period_start("month", date(2026, 12, 1)), date(2026, 12, 1))

        with self.assertRaises(ValueError):
            period_start("year", thursday)


def member(user_id, name=None):
    user = {"id": user_id, "email": "{}@example.com".format(user_id)}

    if name is not None:
        user["display_name"] = name

    return user


def user_steps(user_id, entry_date, count):
    entry = steps(entry_date, count)
    entry["user_id"] = user_id

    return entry


class LeaderboardTestCase(unittest.TestCase):

    START = "2026-11-09"
    END = "2026-11-12"

    def rows(self, members, entries, viewer_id="a", start=None, end=None):
        return leaderboard_rows(
            members, entries, start or self.START, end or self.END, viewer_id
        )

    def test_ranks_by_total_steps_and_sums_multiple_entries(self):
        rows = self.rows(
            [member("a", "Alice"), member("b", "Bob")],
            [
                user_steps("a", "2026-11-12", 5000),
                user_steps("b", "2026-11-10", 4000),
                user_steps("b", "2026-11-12", 2500),
            ],
        )

        self.assertEqual(
            rows,
            [
                {"rank": 1, "user_id": "b", "name": "Bob", "steps": 6500, "is_you": False},
                {"rank": 2, "user_id": "a", "name": "Alice", "steps": 5000, "is_you": True},
            ],
        )

    def test_member_with_no_entries_listed_with_zero(self):
        rows = self.rows(
            [member("a", "Alice"), member("d", "Dana")],
            [user_steps("a", "2026-11-12", 10)],
        )

        self.assertEqual([(row["name"], row["steps"]) for row in rows], [("Alice", 10), ("Dana", 0)])

    def test_ties_share_rank_alphabetical_and_next_rank_skips(self):
        rows = self.rows(
            [member("c", "Cy"), member("b", "Bea"), member("a", "adam")],
            [
                user_steps("a", "2026-11-12", 5000),
                user_steps("b", "2026-11-12", 5000),
                user_steps("c", "2026-11-12", 100),
            ],
        )

        self.assertEqual(
            [(row["rank"], row["name"]) for row in rows],
            [(1, "adam"), (1, "Bea"), (3, "Cy")],
        )

    def test_all_zero_members_share_first_place(self):
        rows = self.rows([member("b", "Bob"), member("a", "Alice")], [])

        self.assertEqual([(row["rank"], row["name"]) for row in rows], [(1, "Alice"), (1, "Bob")])

    def test_marks_viewer_row(self):
        rows = self.rows(
            [member("a", "Alice"), member("b", "Bob")], [], viewer_id="b"
        )

        self.assertEqual([row["user_id"] for row in rows if row["is_you"]], ["b"])

    def test_ignores_entries_from_non_members(self):
        rows = self.rows(
            [member("a", "Alice")],
            [user_steps("z", "2026-11-12", 99999), user_steps("a", "2026-11-12", 1)],
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["steps"], 1)

    def test_future_and_before_start_entries_do_not_count(self):
        rows = self.rows(
            [member("a", "Alice")],
            [
                user_steps("a", "2026-11-13", 7000),
                user_steps("a", "2026-11-08", 8000),
                user_steps("a", "2026-11-09", 3),
                user_steps("a", "2026-11-12", 4),
            ],
        )

        self.assertEqual(rows[0]["steps"], 7)

    def test_week_spanning_month_boundary(self):
        today = date(2026, 12, 2)
        entries = [
            user_steps("a", "2026-11-30", 1000),
            user_steps("a", "2026-12-01", 200),
        ]
        members = [member("a", "Alice")]

        week = self.rows(
            members,
            entries,
            start=period_start("week", today).isoformat(),
            end=today.isoformat(),
        )
        month = self.rows(
            members,
            entries,
            start=period_start("month", today).isoformat(),
            end=today.isoformat(),
        )

        self.assertEqual(week[0]["steps"], 1200)
        self.assertEqual(month[0]["steps"], 200)

    def test_missing_display_name_falls_back_to_member(self):
        rows = self.rows([member("a")], [])

        self.assertEqual(rows[0]["name"], "Member")
        self.assertNotIn("example.com", str(rows))


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

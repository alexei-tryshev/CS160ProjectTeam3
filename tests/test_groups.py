import re
import unittest
from datetime import date, timedelta

from app import create_app
from groups import MAX_GROUP_MEMBERS
from tests.auth_helpers import log_in


TODAY = date.today()
TOMORROW = TODAY + timedelta(days=1)
MONDAY = TODAY - timedelta(days=TODAY.weekday())
FIRST = TODAY.replace(day=1)


def leaderboard(body):
    """Return (rank, name, steps) for each leaderboard row, top first."""

    table = re.search(r'<table class="leaderboard">(.*?)</table>', body, re.S).group(1)
    rows = re.findall(r"<tr[^>]*>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*<td>(.*?)</td>", table, re.S)

    return [tuple(cell.strip() for cell in row) for row in rows]


class GroupsPageTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "USE_MEMORY_DB": True,
                "SECRET_KEY": "test",
            }
        )

        self.repo = self.app.extensions["repository"]
        self.alice, self.alice_id = self.as_user("alice@example.com", "Alice")

    def as_user(self, email, name):
        client = self.app.test_client()
        user_id = log_in(client, self.repo, email, display_name=name)

        return client, user_id

    def create(self, client=None, name="Roommates"):
        client = client or self.alice
        response = client.post("/groups", data={"name": name})

        self.assertEqual(response.status_code, 302)

        group_id = response.headers["Location"].split("group=")[1]

        return self.repo.get_group(group_id)

    def join(self, client, code):
        return client.post(
            "/groups/join",
            data={"code": code},
            follow_redirects=True,
        ).get_data(as_text=True)

    def log(self, user_id, day, count):
        self.repo.create_entry(
            "steps", user_id, {"date": day.isoformat(), "steps": count}
        )

    def view(self, client, group, period=None):
        query = {"group": group["id"]}

        if period:
            query["period"] = period

        return client.get("/groups", query_string=query).get_data(as_text=True)

    def test_requires_login(self):
        response = self.app.test_client().get("/groups")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.headers["Location"])

    def test_nav_has_groups_link_marked_current(self):
        body = self.alice.get("/groups").get_data(as_text=True)

        self.assertIn('href="/groups" aria-current="page"', body)

    def test_dashboard_links_to_groups(self):
        body = self.alice.get("/").get_data(as_text=True)

        self.assertIn("Step groups", body)
        self.assertIn(
            "Compete with friends on daily, weekly, and monthly steps.", body
        )

    def test_legacy_user_sees_only_name_prompt(self):
        legacy, _ = self.as_user("old@example.com", None)

        response = legacy.get("/groups")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Choose a display name", body)
        self.assertIn('action="/groups/display-name"', body)
        self.assertNotIn('action="/groups/join"', body)

    def test_legacy_user_cannot_create_or_join_before_naming(self):
        group = self.create()
        legacy, legacy_id = self.as_user("old@example.com", None)

        created = legacy.post("/groups", data={"name": "Sneaky"})
        joined = legacy.post("/groups/join", data={"code": group["join_code"]})

        self.assertEqual(created.status_code, 302)
        self.assertEqual(joined.status_code, 302)
        self.assertEqual(self.repo.list_groups_for_user(legacy_id), [])

    def test_setting_display_name_unlocks_groups(self):
        legacy, legacy_id = self.as_user("old@example.com", None)

        response = legacy.post("/groups/display-name", data={"display_name": " Joyce "})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.repo.get_user(legacy_id)["display_name"], "Joyce")

        body = legacy.get("/groups").get_data(as_text=True)

        self.assertNotIn("Choose a display name", body)
        self.assertIn('action="/groups/join"', body)

    def test_blank_or_long_display_name_rejected(self):
        legacy, legacy_id = self.as_user("old@example.com", None)

        blank = legacy.post("/groups/display-name", data={"display_name": "   "})

        self.assertEqual(blank.status_code, 400)
        self.assertIn("Display name is required.", blank.get_data(as_text=True))

        long = legacy.post("/groups/display-name", data={"display_name": "x" * 31})

        self.assertEqual(long.status_code, 400)
        self.assertNotIn("display_name", self.repo.get_user(legacy_id))

    def test_empty_state_shows_create_and_join(self):
        body = self.alice.get("/groups").get_data(as_text=True)

        self.assertIn(
            "Create a group and share its code, or join a friend's group with theirs.",
            body,
        )
        self.assertIn('action="/groups"', body)
        self.assertIn('action="/groups/join"', body)
        self.assertNotIn('class="leaderboard"', body)

    def test_create_group_shows_name_and_code(self):
        group = self.create()

        self.assertEqual(group["member_ids"], [self.alice_id])

        body = self.alice.get("/groups").get_data(as_text=True)

        self.assertIn("Roommates", body)
        self.assertIn(group["join_code"], body)
        self.assertIn(
            "Group created. Share the code {}.".format(group["join_code"]), body
        )
        self.assertEqual(leaderboard(body), [("1", "You (Alice)", "0")])

    def test_create_group_name_validation(self):
        blank = self.alice.post("/groups", data={"name": "  "}, follow_redirects=True)

        self.assertIn("Group name is required.", blank.get_data(as_text=True))

        long = self.alice.post("/groups", data={"name": "x" * 41}, follow_redirects=True)

        self.assertIn(
            "Group name must be at most 40 characters.",
            long.get_data(as_text=True),
        )
        self.assertEqual(self.repo.list_groups_for_user(self.alice_id), [])

    def test_join_with_lowercase_padded_code(self):
        group = self.create()
        bob, bob_id = self.as_user("bob@example.com", "Bob")

        body = self.join(bob, "  {} ".format(group["join_code"].lower()))

        self.assertIn("You joined Roommates.", body)
        self.assertIn(bob_id, self.repo.get_group(group["id"])["member_ids"])
        self.assertIn("You (Bob)", body)

    def test_join_wrong_code(self):
        bob, bob_id = self.as_user("bob@example.com", "Bob")

        for bad in ("ZZZZZZ", ""):
            with self.subTest(code=bad):
                self.assertIn("No group has that code.", self.join(bob, bad))

        self.assertEqual(self.repo.list_groups_for_user(bob_id), [])

    def test_join_twice_is_friendly_and_not_duplicated(self):
        group = self.create()
        bob, bob_id = self.as_user("bob@example.com", "Bob")
        self.log(bob_id, TODAY, 1000)

        self.join(bob, group["join_code"])
        body = self.join(bob, group["join_code"])

        self.assertIn("already in Roommates.", body)
        self.assertEqual(
            self.repo.get_group(group["id"])["member_ids"].count(bob_id), 1
        )
        self.assertEqual(
            leaderboard(self.view(bob, group)),
            [("1", "You (Bob)", "1,000"), ("2", "Alice", "0")],
        )

    def test_join_full_group(self):
        group = self.create()

        for index in range(MAX_GROUP_MEMBERS - 1):
            self.repo.add_group_member(group["id"], "filler-{}".format(index))

        bob, bob_id = self.as_user("bob@example.com", "Bob")

        self.assertIn("That group is full.", self.join(bob, group["join_code"]))
        self.assertNotIn(bob_id, self.repo.get_group(group["id"])["member_ids"])

    def test_leaderboard_orders_by_today_steps_with_zero_members(self):
        group = self.create()
        bob, bob_id = self.as_user("bob@example.com", "Bob")
        dana, _ = self.as_user("dana@example.com", "Dana")
        self.join(bob, group["join_code"])
        self.join(dana, group["join_code"])

        self.log(self.alice_id, TODAY, 5000)
        self.log(self.alice_id, TODAY, 1200)
        self.log(bob_id, TODAY, 9000)

        self.assertEqual(
            leaderboard(self.view(self.alice, group)),
            [
                ("1", "Bob", "9,000"),
                ("2", "You (Alice)", "6,200"),
                ("3", "Dana", "0"),
            ],
        )

    def test_period_switch(self):
        group = self.create()
        bob, bob_id = self.as_user("bob@example.com", "Bob")
        self.join(bob, group["join_code"])

        self.log(self.alice_id, TODAY, 5000)
        self.log(bob_id, FIRST, 20000)

        def leader(period):
            return leaderboard(self.view(self.alice, group, period))[0][1]

        self.assertEqual(leader("month"), "Bob")
        self.assertEqual(leader("week"), "Bob" if FIRST >= MONDAY else "You (Alice)")

        if FIRST != TODAY:
            self.assertEqual(leader("today"), "You (Alice)")
            self.assertEqual(leader("zzz"), "You (Alice)")
            self.assertEqual(leader(None), "You (Alice)")

        body = self.view(self.alice, group, "month")

        self.assertIn(
            'href="/groups?group={}&amp;period=month" aria-current="true"'.format(
                group["id"]
            ),
            body,
        )

    def test_future_dated_steps_do_not_count(self):
        group = self.create()
        bob, bob_id = self.as_user("bob@example.com", "Bob")
        self.join(bob, group["join_code"])
        self.log(bob_id, TOMORROW, 50000)

        for period in ("today", "week", "month"):
            with self.subTest(period=period):
                rows = leaderboard(self.view(self.alice, group, period))

                self.assertIn(("1", "Bob", "0"), rows)
                self.assertNotIn("50,000", self.view(self.alice, group, period))

    def test_viewer_row_marked_you(self):
        group = self.create()
        bob, _ = self.as_user("bob@example.com", "Bob")
        self.join(bob, group["join_code"])

        body = self.view(self.alice, group)
        you_rows = re.findall(r'<tr class="is-you">(.*?)</tr>', body, re.S)

        self.assertEqual(len(you_rows), 1)
        self.assertIn("You (Alice)", you_rows[0])

    def test_emails_never_shown(self):
        group = self.create()
        bob, bob_id = self.as_user("bob@example.com", "Bob")
        self.join(bob, group["join_code"])
        self.log(bob_id, TODAY, 10)

        for period in ("today", "week", "month"):
            with self.subTest(period=period):
                self.assertNotIn(
                    "bob@example.com", self.view(self.alice, group, period)
                )

    def test_names_are_escaped(self):
        tricky, _ = self.as_user("tricky@example.com", "<b>x</b>")
        group = self.create(client=tricky, name="<i>g</i>")
        self.join(self.alice, group["join_code"])

        body = self.view(self.alice, group)

        self.assertIn("&lt;b&gt;x&lt;/b&gt;", body)
        self.assertIn("&lt;i&gt;g&lt;/i&gt;", body)
        self.assertNotIn("<b>x</b>", body)
        self.assertNotIn("<i>g</i>", body)

    def test_non_member_gets_404(self):
        group = self.create()
        carol, _ = self.as_user("carol@example.com", "Carol")

        response = carol.get("/groups", query_string={"group": group["id"]})

        self.assertEqual(response.status_code, 404)
        self.assertNotIn("Roommates", response.get_data(as_text=True))
        self.assertEqual(
            carol.post("/groups/{}/leave".format(group["id"])).status_code, 404
        )
        self.assertEqual(
            self.repo.get_group(group["id"])["member_ids"], [self.alice_id]
        )

    def test_garbage_group_id_gets_404(self):
        self.create()

        self.assertEqual(
            self.alice.get("/groups", query_string={"group": "abc"}).status_code,
            404,
        )
        self.assertEqual(self.alice.post("/groups/abc/leave").status_code, 404)

    def test_switch_between_two_groups(self):
        first = self.create(name="Roommates")
        second = self.create(name="Lab crew")

        # The first view shows the "Group created" messages, codes included.
        self.alice.get("/groups")

        default = self.alice.get("/groups").get_data(as_text=True)

        self.assertIn(
            'href="/groups?group={}" aria-current="true"'.format(first["id"]),
            default,
        )
        self.assertIn(first["join_code"], default)
        self.assertNotIn(second["join_code"], default)

        other = self.view(self.alice, second)

        self.assertIn(
            'href="/groups?group={}" aria-current="true"'.format(second["id"]),
            other,
        )
        self.assertIn(second["join_code"], other)
        self.assertNotIn(first["join_code"], other)

    def test_leave_group(self):
        group = self.create()
        bob, bob_id = self.as_user("bob@example.com", "Bob")
        self.join(bob, group["join_code"])

        self.assertIn("return confirm('Leave this group?')", self.view(bob, group))

        response = bob.post(
            "/groups/{}/leave".format(group["id"]), follow_redirects=True
        )

        self.assertIn("You left Roommates.", response.get_data(as_text=True))
        self.assertEqual(
            self.repo.get_group(group["id"])["member_ids"], [self.alice_id]
        )
        self.assertEqual(
            bob.get("/groups", query_string={"group": group["id"]}).status_code,
            404,
        )

    def test_last_member_leaving_deletes_group(self):
        group = self.create()

        self.alice.post("/groups/{}/leave".format(group["id"]))

        self.assertIsNone(self.repo.get_group(group["id"]))

        bob, _ = self.as_user("bob@example.com", "Bob")

        self.assertIn("No group has that code.", self.join(bob, group["join_code"]))

    def test_rejoin_after_leaving(self):
        group = self.create()
        bob, bob_id = self.as_user("bob@example.com", "Bob")
        self.join(bob, group["join_code"])
        bob.post("/groups/{}/leave".format(group["id"]))

        self.assertIn("You joined Roommates.", self.join(bob, group["join_code"]))
        self.assertIn(bob_id, self.repo.get_group(group["id"])["member_ids"])

    def test_steps_page_unaffected_by_group_membership(self):
        self.log(self.alice_id, TODAY, 4321)

        # Clear the "logged in" message so both views are message-free.
        self.alice.get("/steps")

        before = self.alice.get("/steps").get_data(as_text=True)

        group = self.create()
        self.view(self.alice, group)

        self.assertEqual(self.alice.get("/steps").get_data(as_text=True), before)


if __name__ == "__main__":
    unittest.main()

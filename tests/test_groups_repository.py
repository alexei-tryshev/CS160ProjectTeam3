import unittest

from groups import (
    JOIN_CODE_ALPHABET,
    JOIN_CODE_LENGTH,
    MAX_GROUP_MEMBERS,
    generate_join_code,
    normalize_join_code,
)
from repository import InMemoryRepository
from validation import validate_group_name


def code_sequence(*codes):
    remaining = list(codes)

    def factory():
        return remaining.pop(0) if len(remaining) > 1 else remaining[0]

    return factory


class JoinCodeTestCase(unittest.TestCase):

    def test_generate_join_code_shape(self):
        codes = [generate_join_code() for _ in range(200)]

        for code in codes:
            self.assertEqual(len(code), JOIN_CODE_LENGTH)
            self.assertTrue(set(code) <= set(JOIN_CODE_ALPHABET))
            self.assertFalse(set(code) & set("0O1IL"))

        self.assertGreater(len(set(codes)), 190)

    def test_normalize_join_code(self):
        self.assertEqual(normalize_join_code("  k7qm2x "), "K7QM2X")
        self.assertEqual(normalize_join_code(None), "")

    def test_validate_group_name(self):
        self.assertEqual(validate_group_name({"name": "  Roommates "}), ("Roommates", []))
        self.assertEqual(
            validate_group_name({"name": "   "})[1],
            ["Group name is required."],
        )
        self.assertEqual(validate_group_name({})[1], ["Group name is required."])
        self.assertEqual(
            validate_group_name({"name": "x" * 41})[1],
            ["Group name must be at most 40 characters."],
        )
        self.assertEqual(validate_group_name({"name": "x" * 40})[1], [])


class GroupsContract:

    def user(self, name):
        return self.repo.create_user(
            "{}@example.com".format(name.lower()), "hash", display_name=name
        )["id"]

    def test_create_group_makes_creator_sole_member(self):
        alice = self.user("Alice")

        group = self.repo.create_group("Roommates", alice)

        self.assertEqual(group["name"], "Roommates")
        self.assertEqual(group["member_ids"], [alice])
        self.assertEqual(group["created_by"], alice)
        self.assertEqual(len(group["join_code"]), JOIN_CODE_LENGTH)
        self.assertEqual(self.repo.get_group(group["id"]), group)

    def test_create_group_trims_name_and_rejects_blank_and_41_chars(self):
        alice = self.user("Alice")

        self.assertEqual(self.repo.create_group("  Lab crew ", alice)["name"], "Lab crew")
        self.assertEqual(len(self.repo.create_group("x" * 40, alice)["name"]), 40)

        for bad in ("", "   ", "x" * 41, None):
            with self.subTest(name=bad):
                with self.assertRaises(ValueError):
                    self.repo.create_group(bad, alice)

        self.assertEqual(len(self.repo.list_groups_for_user(alice)), 2)

    def test_create_group_retries_on_code_collision(self):
        alice = self.user("Alice")

        first = self.repo.create_group("One", alice, code_factory=lambda: "AAAAAA")
        second = self.repo.create_group(
            "Two", alice, code_factory=code_sequence("AAAAAA", "AAAAAA", "BBBBBB")
        )

        self.assertEqual(first["join_code"], "AAAAAA")
        self.assertEqual(second["join_code"], "BBBBBB")

    def test_create_group_gives_up_after_ten_collisions(self):
        alice = self.user("Alice")
        calls = []

        def factory():
            calls.append(1)
            return "AAAAAA"

        self.repo.create_group("One", alice, code_factory=lambda: "AAAAAA")

        with self.assertRaises(RuntimeError):
            self.repo.create_group("Two", alice, code_factory=factory)

        self.assertEqual(len(calls), 10)
        self.assertEqual(len(self.repo.list_groups_for_user(alice)), 1)

    def test_get_group_by_code_is_case_and_space_insensitive(self):
        alice = self.user("Alice")
        group = self.repo.create_group("One", alice, code_factory=lambda: "K7QM2X")

        self.assertEqual(self.repo.get_group_by_code("  k7qm2x ")["id"], group["id"])
        self.assertIsNone(self.repo.get_group_by_code("ZZZZZZ"))
        self.assertIsNone(self.repo.get_group_by_code(""))

    def test_get_group_with_garbage_id_returns_none(self):
        self.assertIsNone(self.repo.get_group("abc"))
        self.assertIsNone(self.repo.get_group(""))
        self.assertIsNone(self.repo.get_group("0123456789abcdef01234567"))

    def test_add_member_results(self):
        alice, bob = self.user("Alice"), self.user("Bob")
        group = self.repo.create_group("One", alice)

        self.assertEqual(self.repo.add_group_member(group["id"], bob), "joined")
        self.assertEqual(self.repo.add_group_member(group["id"], bob), "already_member")
        self.assertEqual(self.repo.add_group_member(group["id"], alice), "already_member")
        self.assertEqual(self.repo.get_group(group["id"])["member_ids"], [alice, bob])
        self.assertEqual(self.repo.add_group_member("abc", bob), "not_found")
        self.assertEqual(
            self.repo.add_group_member("0123456789abcdef01234567", bob),
            "not_found",
        )

    def test_group_full_at_50(self):
        alice = self.user("Alice")
        group = self.repo.create_group("One", alice)

        for index in range(MAX_GROUP_MEMBERS - 1):
            self.assertEqual(
                self.repo.add_group_member(group["id"], "user-{}".format(index)),
                "joined",
            )

        self.assertEqual(self.repo.add_group_member(group["id"], "late"), "full")
        self.assertEqual(self.repo.add_group_member(group["id"], alice), "already_member")
        self.assertEqual(
            len(self.repo.get_group(group["id"])["member_ids"]),
            MAX_GROUP_MEMBERS,
        )

    def test_list_groups_for_user_only_their_groups_oldest_first(self):
        alice, bob = self.user("Alice"), self.user("Bob")
        first = self.repo.create_group("First", alice)
        self.repo.create_group("Bob only", bob)
        second = self.repo.create_group("Second", bob)
        self.repo.add_group_member(second["id"], alice)

        self.assertEqual(
            [group["name"] for group in self.repo.list_groups_for_user(alice)],
            ["First", "Second"],
        )
        self.assertEqual(self.repo.list_groups_for_user("nobody"), [])
        self.assertEqual(first["member_ids"], [alice])

    def test_remove_member_and_last_member_deletes_group(self):
        alice, bob = self.user("Alice"), self.user("Bob")
        group = self.repo.create_group("One", alice)
        self.repo.add_group_member(group["id"], bob)

        self.assertFalse(self.repo.remove_group_member(group["id"], "stranger"))
        self.assertFalse(self.repo.remove_group_member("abc", alice))
        self.assertTrue(self.repo.remove_group_member(group["id"], alice))
        self.assertEqual(self.repo.get_group(group["id"])["member_ids"], [bob])
        self.assertTrue(self.repo.remove_group_member(group["id"], bob))
        self.assertIsNone(self.repo.get_group(group["id"]))
        self.assertIsNone(self.repo.get_group_by_code(group["join_code"]))
        self.assertEqual(self.repo.list_groups_for_user(bob), [])

    def test_list_users_returns_requested_users_and_skips_unknown(self):
        alice, bob = self.user("Alice"), self.user("Bob")
        self.user("Carol")

        users = self.repo.list_users([alice, bob, "abc", "0123456789abcdef01234567"])

        self.assertEqual(
            sorted(user["display_name"] for user in users),
            ["Alice", "Bob"],
        )
        self.assertEqual({user["id"] for user in users}, {alice, bob})
        self.assertEqual(self.repo.list_users([]), [])

    def test_list_entries_for_users_in_range(self):
        def log(user_id, day, count):
            self.repo.create_entry("steps", user_id, {"date": day, "steps": count})

        log("alice", "2026-11-09", 100)
        log("alice", "2026-11-12", 200)
        log("bob", "2026-11-10", 300)
        log("alice", "2026-11-08", 9000)
        log("bob", "2026-11-13", 9000)
        log("carol", "2026-11-10", 9000)
        self.repo.create_entry(
            "water", "alice", {"date": "2026-11-10", "amount_oz": 64}
        )

        entries = self.repo.list_entries_for_users_in_range(
            "steps", ["alice", "bob"], "2026-11-09", "2026-11-12"
        )

        self.assertEqual(
            sorted((entry["user_id"], entry["data"]["steps"]) for entry in entries),
            [("alice", 100), ("alice", 200), ("bob", 300)],
        )
        self.assertEqual(
            self.repo.list_entries_for_users_in_range(
                "steps", [], "2026-11-09", "2026-11-12"
            ),
            [],
        )


class InMemoryGroupsTestCase(GroupsContract, unittest.TestCase):

    def setUp(self):
        self.repo = InMemoryRepository()


if __name__ == "__main__":
    unittest.main()

"""Group storage against a real MongoDB. Skipped when MongoDB is not reachable."""

import re
import unittest
from datetime import date

from app import create_app
from tests.auth_helpers import log_in
from tests.mongo_support import (
    close_after_test,
    drop_test_database,
    mongo_repository_or_skip,
)
from tests.test_groups_repository import GroupsContract


class MongoGroupsTestCase(GroupsContract, unittest.TestCase):

    def setUp(self):
        self.repo = mongo_repository_or_skip()
        drop_test_database(self.repo)
        self.repo.ensure_indexes()
        close_after_test(self, self.repo)


class MongoGroupsPageTestCase(unittest.TestCase):

    def setUp(self):
        self.repo = mongo_repository_or_skip()
        drop_test_database(self.repo)
        self.repo.ensure_indexes()
        close_after_test(self, self.repo)

        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test",
                "REPOSITORY": self.repo,
            }
        )

    def test_group_leaderboard_round_trip(self):
        today = date.today().isoformat()
        alice, bob = self.app.test_client(), self.app.test_client()
        log_in(alice, self.repo, "alice@example.com", display_name="Alice")
        log_in(bob, self.repo, "bob@example.com", display_name="Bob")

        alice.post("/groups", data={"name": "Roommates"})

        group = self.repo.database["groups"].find_one({"name": "Roommates"})

        bob.post("/groups/join", data={"code": group["join_code"].lower()})
        alice.post("/steps", data={"date": today, "steps": "3000"})
        bob.post("/steps", data={"date": today, "steps": "7000"})

        body = alice.get("/groups?period=today").get_data(as_text=True)
        names = re.findall(r"<td>\s*((?:You \()?(?:Alice|Bob)\)?)\s*</td>", body)

        self.assertEqual(names, ["Bob", "You (Alice)"])
        self.assertIn("7,000", body)
        self.assertNotIn("bob@example.com", body)

        group_id = str(group["_id"])
        alice.post("/groups/{}/leave".format(group_id))
        bob.post("/groups/{}/leave".format(group_id))

        self.assertEqual(self.repo.database["groups"].count_documents({}), 0)


if __name__ == "__main__":
    unittest.main()

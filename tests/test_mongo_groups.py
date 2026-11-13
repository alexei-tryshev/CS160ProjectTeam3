"""Group storage against a real MongoDB. Skipped when MongoDB is not reachable."""

import unittest

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


if __name__ == "__main__":
    unittest.main()

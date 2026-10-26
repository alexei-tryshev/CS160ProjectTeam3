import unittest

from repository import InMemoryRepository
from tests.mongo_support import (
    close_after_test,
    drop_test_database,
    mongo_repository_or_skip,
)


class RepositoryContract:

    def make_repository(self):
        raise NotImplementedError

    def setUp(self):
        self.repo = self.make_repository()

    def test_list_entries_in_range_is_inclusive_and_ascending(self):
        for d in ["2026-10-01", "2026-10-03", "2026-10-05", "2026-10-07"]:
            self.repo.create_entry("water", "u1", {"date": d, "amount_ml": 100})
        self.repo.create_entry("water", "u2", {"date": "2026-10-03", "amount_ml": 1})
        self.repo.create_entry("weight", "u1", {"date": "2026-10-03", "weight_kg": 70.0})

        dates = [
            entry["date"]
            for entry in self.repo.list_entries_in_range(
                "water", "u1", "2026-10-03", "2026-10-05"
            )
        ]

        self.assertEqual(dates, ["2026-10-03", "2026-10-05"])
        self.assertEqual(len(self.repo.list_entries_in_range("water", "u1")), 4)

    def test_list_entries_in_range_has_no_twenty_entry_cap(self):
        for i in range(25):
            self.repo.create_entry("water", "u1", {"date": "2026-10-01", "amount_ml": i})

        self.assertEqual(len(self.repo.list_entries_in_range("water", "u1")), 25)

    def test_delete_entry_removes_only_matching_entry(self):
        entry = self.repo.create_entry("water", "u1", {"date": "2026-10-01", "amount_ml": 250})

        self.assertFalse(self.repo.delete_entry(entry["id"], "weight", "u1"))
        self.assertFalse(self.repo.delete_entry(entry["id"], "water", "u2"))
        self.assertFalse(self.repo.delete_entry("not-a-real-id", "water", "u1"))
        self.assertTrue(self.repo.delete_entry(entry["id"], "water", "u1"))
        self.assertIsNone(self.repo.get_entry(entry["id"], "water", "u1"))

    def test_water_goal_defaults_to_none_then_persists_and_updates(self):
        self.assertIsNone(self.repo.get_water_goal("u1"))
        self.assertEqual(self.repo.set_water_goal("u1", 2500), 2500)
        self.assertEqual(self.repo.set_water_goal("u1", 3000), 3000)
        self.assertEqual(self.repo.get_water_goal("u1"), 3000)
        self.assertIsNone(self.repo.get_water_goal("u2"))

    def test_rejects_integers_too_large_for_mongodb(self):
        with self.assertRaises(ValueError):
            self.repo.create_entry("water", "u1", {"date": "2026-10-01", "amount_ml": 2 ** 63})

        with self.assertRaises(ValueError):
            self.repo.set_water_goal("u1", 2 ** 63)

        self.assertEqual(self.repo.list_entries("water", "u1"), [])
        self.assertIsNone(self.repo.get_water_goal("u1"))

    def test_set_water_goal_rejects_invalid_values(self):
        for bad in (0, -5, 2.5, True):
            with self.assertRaises(ValueError):
                self.repo.set_water_goal("u1", bad)

        self.assertIsNone(self.repo.get_water_goal("u1"))


class InMemoryRepositoryTests(RepositoryContract, unittest.TestCase):

    def make_repository(self):
        return InMemoryRepository()


class MongoRepositoryTests(RepositoryContract, unittest.TestCase):

    def make_repository(self):
        repository = mongo_repository_or_skip()
        drop_test_database(repository)
        repository.ensure_indexes()
        close_after_test(self, repository)
        return repository


if __name__ == "__main__":
    unittest.main()

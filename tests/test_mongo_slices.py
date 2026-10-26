"""Water and Weight vertical slices against a real MongoDB.

Each test drives the Flask pages and then reads MongoDB directly to
prove the data was stored, updated, and deleted. Skipped when MongoDB
is not reachable.
"""

import unittest
from datetime import date, timedelta

from app import create_app
from tests.mongo_support import (
    TEST_DB_NAME,
    close_after_test,
    drop_test_database,
    mongo_repository_or_skip,
)


TODAY = date.today().isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()


class MongoVerticalSliceTestCase(unittest.TestCase):

    def setUp(self):
        self.repo = mongo_repository_or_skip()
        drop_test_database(self.repo)
        close_after_test(self, self.repo)

        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test",
                "REPOSITORY": self.repo,
            }
        )

        self.client = self.app.test_client()

    def test_water_slice_round_trip(self):
        self.client.post("/water", data={"date": TODAY, "amount_ml": "750"})

        doc = self.repo.collection.find_one({"feature": "water", "user_id": "demo-user"})

        self.assertEqual(doc["data"], {"date": TODAY, "amount_ml": 750})
        self.assertEqual(self.repo.database.name, TEST_DB_NAME)
        self.assertIn("750", self.client.get("/water").get_data(as_text=True))

        entry_id = str(doc["_id"])

        self.client.post(
            "/water",
            data={"entry_id": entry_id, "date": TODAY, "amount_ml": "900"},
        )

        self.assertEqual(
            self.repo.collection.find_one({"_id": doc["_id"]})["data"]["amount_ml"],
            900,
        )

        self.client.post("/water/goal", data={"water_goal_ml": "2500"})

        self.assertEqual(
            self.repo.goals_collection.find_one({"user_id": "demo-user"})["water_goal_ml"],
            2500,
        )

        body = self.client.get("/water").get_data(as_text=True)

        self.assertIn("900", body)
        self.assertIn("/ 2,500 mL", body)

        self.client.post(f"/water/entries/{entry_id}/delete")

        self.assertIsNone(self.repo.collection.find_one({"_id": doc["_id"]}))

    def test_weight_slice_round_trip(self):
        self.client.post("/weight", data={"date": YESTERDAY, "weight_kg": "69.3"})
        self.client.post("/weight", data={"date": TODAY, "weight_kg": "68.5"})

        docs = list(self.repo.collection.find({"feature": "weight"}).sort("date", 1))

        self.assertEqual([doc["data"]["weight_kg"] for doc in docs], [69.3, 68.5])

        body = self.client.get("/weight").get_data(as_text=True)

        self.assertIn("68.5 kg", body)
        self.assertIn("−0.8 kg", body)

        self.client.post(
            "/weight",
            data={"entry_id": str(docs[1]["_id"]), "date": TODAY, "weight_kg": "68.9"},
        )

        self.assertEqual(
            self.repo.collection.find_one({"_id": docs[1]["_id"]})["data"]["weight_kg"],
            68.9,
        )

        self.client.post(f"/weight/entries/{docs[0]['_id']}/delete")

        self.assertEqual(self.repo.collection.count_documents({"feature": "weight"}), 1)

    def test_api_reads_back_what_the_form_stored(self):
        self.client.post("/water", data={"date": TODAY, "amount_ml": "300"})

        entries = self.client.get("/api/entries/water").get_json()["entries"]

        self.assertEqual(entries[0]["data"]["amount_ml"], 300)


if __name__ == "__main__":
    unittest.main()

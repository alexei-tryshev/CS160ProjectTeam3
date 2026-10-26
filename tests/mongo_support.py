import os
import unittest

from repository import MongoRepository


TEST_DB_NAME = "wellness_tracker_test"


def mongo_repository_or_skip() -> MongoRepository:
    uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")

    try:
        repository = MongoRepository(
            uri=uri,
            database_name=TEST_DB_NAME,
            timeout_ms=500,
        )
        repository.ping()
    except Exception:
        raise unittest.SkipTest(
            "MongoDB not reachable at {}; "
            "skipping real-MongoDB tests.".format(uri)
        )

    return repository


def drop_test_database(repository: MongoRepository) -> None:
    repository.client.drop_database(TEST_DB_NAME)

import os
import unittest

from repository import MongoRepository


TEST_DB_NAME = "wellness_tracker_test"


def mongo_repository_or_skip() -> MongoRepository:
    uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")

    repository = MongoRepository(
        uri=uri,
        database_name=TEST_DB_NAME,
        timeout_ms=500,
    )

    try:
        repository.ping()
    except Exception:
        repository.client.close()
        raise unittest.SkipTest(
            "MongoDB not reachable at {}; "
            "skipping real-MongoDB tests.".format(uri)
        )

    return repository


def drop_test_database(repository: MongoRepository) -> None:
    repository.client.drop_database(TEST_DB_NAME)


def close_after_test(test_case: unittest.TestCase, repository: MongoRepository) -> None:
    """Drop the test database, then close the client, when the test ends."""

    test_case.addCleanup(repository.client.close)
    test_case.addCleanup(drop_test_database, repository)

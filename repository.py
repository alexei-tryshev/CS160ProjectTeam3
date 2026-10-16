from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _serialize_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(entry)

    if "_id" in result:
        result["id"] = str(result.pop("_id"))

    return result


class InMemoryRepository:


    def __init__(self) -> None:
        self._entries: List[Dict[str, Any]] = []

    def add_entry(
        self,
        feature: str,
        user_id: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        entry = {
            "id": str(uuid4()),
            "feature": feature,
            "user_id": user_id,
            "date": payload["date"],
            "data": dict(payload),
            "created_at": _utc_now(),
        }

        self._entries.append(entry)
        return dict(entry)

    def list_entries(
        self,
        feature: str,
        user_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        entries = [
            entry
            for entry in self._entries
            if entry["feature"] == feature
            and entry["user_id"] == user_id
        ]

        entries.sort(
            key=lambda item: (
                item["date"],
                item["created_at"],
            ),
            reverse=True,
        )

        return [dict(entry) for entry in entries[:limit]]


class MongoRepository:


    def __init__(
        self,
        uri: str,
        database_name: str,
        timeout_ms: int = 1000,
    ) -> None:
        from pymongo import MongoClient

        self.client = MongoClient(
            uri,
            serverSelectionTimeoutMS=timeout_ms,
        )

        self.collection = self.client[database_name]["entries"]

    def ping(self) -> None:
        self.client.admin.command("ping")

    def add_entry(
        self,
        feature: str,
        user_id: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        document = {
            "feature": feature,
            "user_id": user_id,
            "date": payload["date"],
            "data": dict(payload),
            "created_at": _utc_now(),
        }

        result = self.collection.insert_one(document)
        document["_id"] = result.inserted_id

        return _serialize_entry(document)

    def list_entries(
        self,
        feature: str,
        user_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        documents = (
            self.collection
            .find(
                {
                    "feature": feature,
                    "user_id": user_id,
                }
            )
            .sort(
                [
                    ("date", -1),
                    ("created_at", -1),
                ]
            )
            .limit(limit)
        )

        return [
            _serialize_entry(document)
            for document in documents
        ]
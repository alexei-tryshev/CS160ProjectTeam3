from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from schema import (
    ENTRIES_COLLECTION,
    ENTRY_INDEXES,
    GOAL_INDEXES,
    GOALS_COLLECTION,
    USER_INDEXES,
    USERS_COLLECTION,
    validate_entry_document_shape,
    validate_goal_document_shape,
    validate_user_document_shape,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _limit_value(limit: int) -> int:

    try:
        value = int(limit)
    except (TypeError, ValueError):
        value = 20

    return max(1, min(value, 100))


def _normalize_email(email: Any) -> Any:
    if isinstance(email, str):
        return email.strip().lower()

    return email


def _to_object_id(value: str):

    from bson import ObjectId
    from bson.errors import InvalidId

    try:
        return ObjectId(str(value))
    except (InvalidId, TypeError, ValueError):
        return None


def _serialize_document(
    document: Dict[str, Any],
) -> Dict[str, Any]:
    result = deepcopy(document)

    if "_id" in result:
        result["id"] = str(result.pop("_id"))

    return result


def _entry_document(
    feature: str,
    user_id: str,
    payload: Dict[str, Any],
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "feature": feature,
        "user_id": user_id,
        "date": payload.get("date"),
        "data": deepcopy(payload),
        "created_at": created_at or _utc_now(),
    }


def _user_document(
    email: str,
    password_hash: str,
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "email": _normalize_email(email),
        "password_hash": password_hash,
        "created_at": created_at or _utc_now(),
    }


def _goal_document(
    user_id: str,
    water_goal_oz: int,
) -> Dict[str, Any]:
    return {
        "user_id": user_id,
        "water_goal_oz": water_goal_oz,
        "updated_at": _utc_now(),
    }


def _raise_goal_validation_error(
    document: Dict[str, Any],
) -> None:
    errors = validate_goal_document_shape(document)

    if errors:
        raise ValueError(
            "Invalid goal data: {}".format(
                " ".join(errors)
            )
        )


def _in_date_range(
    value: str,
    start_date: Optional[str],
    end_date: Optional[str],
) -> bool:
    if start_date is not None and value < start_date:
        return False

    if end_date is not None and value > end_date:
        return False

    return True


def validate_entry_data(
    feature: str,
    user_id: str,
    payload: Dict[str, Any],
) -> List[str]:

    if not isinstance(payload, dict):
        return ["Entry payload must be an object."]

    document = _entry_document(
        feature,
        user_id,
        payload,
    )

    return validate_entry_document_shape(document)


def validate_user_data(
    email: str,
    password_hash: str,
) -> List[str]:

    document = _user_document(
        email,
        password_hash,
    )

    return validate_user_document_shape(document)


def _validate_entry_document(
    document: Dict[str, Any],
) -> None:
    errors = validate_entry_document_shape(document)

    if errors:
        raise ValueError(
            "Invalid entry document: {}".format(
                " ".join(errors)
            )
        )


def _raise_entry_validation_error(
    feature: str,
    user_id: str,
    payload: Dict[str, Any],
) -> None:
    errors = validate_entry_data(
        feature,
        user_id,
        payload,
    )

    if errors:
        raise ValueError(
            "Invalid entry data: {}".format(
                " ".join(errors)
            )
        )


def _raise_user_validation_error(
    email: str,
    password_hash: str,
) -> None:
    errors = validate_user_data(
        email,
        password_hash,
    )

    if errors:
        raise ValueError(
            "Invalid user data: {}".format(
                " ".join(errors)
            )
        )


class InMemoryRepository:

    def __init__(self) -> None:
        self._entries: List[Dict[str, Any]] = []
        self._users: List[Dict[str, Any]] = []
        self._goals: Dict[str, Dict[str, Any]] = {}

    def create_entry(
        self,
        feature: str,
        user_id: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        _raise_entry_validation_error(
            feature,
            user_id,
            payload,
        )

        entry = _entry_document(
            feature,
            user_id,
            payload,
        )
        entry["id"] = str(uuid4())

        self._entries.append(deepcopy(entry))

        return deepcopy(entry)

    def add_entry(
        self,
        feature: str,
        user_id: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:

        return self.create_entry(
            feature,
            user_id,
            payload,
        )

    def get_entry(
        self,
        entry_id: str,
        feature: str,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        for entry in self._entries:
            if (
                entry["id"] == str(entry_id)
                and entry["feature"] == feature
                and entry["user_id"] == user_id
            ):
                return deepcopy(entry)

        return None

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

        return deepcopy(
            entries[:_limit_value(limit)]
        )

    def list_entries_in_range(
        self,
        feature: str,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        entries = [
            entry
            for entry in self._entries
            if entry["feature"] == feature
            and entry["user_id"] == user_id
            and _in_date_range(
                entry["date"],
                start_date,
                end_date,
            )
        ]

        entries.sort(
            key=lambda item: (
                item["date"],
                item["created_at"],
            )
        )

        return deepcopy(entries)

    def delete_entry(
        self,
        entry_id: str,
        feature: str,
        user_id: str,
    ) -> bool:
        for index, entry in enumerate(self._entries):
            if (
                entry["id"] == str(entry_id)
                and entry["feature"] == feature
                and entry["user_id"] == user_id
            ):
                del self._entries[index]
                return True

        return False

    def get_water_goal(
        self,
        user_id: str,
    ) -> Optional[int]:
        goal = self._goals.get(user_id)

        if goal is None:
            return None

        return goal["water_goal_oz"]

    def set_water_goal(
        self,
        user_id: str,
        water_goal_oz: int,
    ) -> int:
        document = _goal_document(
            user_id,
            water_goal_oz,
        )

        _raise_goal_validation_error(document)

        self._goals[user_id] = document

        return water_goal_oz

    def update_entry(
        self,
        entry_id: str,
        feature: str,
        user_id: str,
        payload: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        _raise_entry_validation_error(
            feature,
            user_id,
            payload,
        )

        for index, entry in enumerate(self._entries):
            if (
                entry["id"] == str(entry_id)
                and entry["feature"] == feature
                and entry["user_id"] == user_id
            ):
                updated = deepcopy(entry)
                updated["date"] = payload["date"]
                updated["data"] = deepcopy(payload)
                self._entries[index] = updated
                return deepcopy(updated)

        return None

    def create_user(
        self,
        email: str,
        password_hash: str,
    ) -> Dict[str, Any]:
        _raise_user_validation_error(
            email,
            password_hash,
        )

        normalized_email = _normalize_email(email)

        if self.get_user_by_email(normalized_email):
            raise ValueError(
                "A user with that email already exists."
            )

        user = _user_document(
            email,
            password_hash,
        )
        user["id"] = str(uuid4())

        self._users.append(deepcopy(user))

        return deepcopy(user)

    def get_user(
        self,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        for user in self._users:
            if user["id"] == str(user_id):
                return deepcopy(user)

        return None

    def get_user_by_email(
        self,
        email: str,
    ) -> Optional[Dict[str, Any]]:
        normalized_email = _normalize_email(email)

        for user in self._users:
            if user["email"] == normalized_email:
                return deepcopy(user)

        return None

    def update_user(
        self,
        user_id: str,
        updates: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(updates, dict):
            raise ValueError(
                "User updates must be an object."
            )

        allowed_fields = {
            "email",
            "password_hash",
        }

        unknown_fields = set(updates) - allowed_fields

        if unknown_fields:
            raise ValueError(
                "User updates contain unsupported fields: {}.".format(
                    ", ".join(sorted(unknown_fields))
                )
            )

        for index, user in enumerate(self._users):
            if user["id"] != str(user_id):
                continue

            updated = deepcopy(user)

            if "email" in updates:
                updated["email"] = _normalize_email(
                    updates["email"]
                )

            if "password_hash" in updates:
                updated["password_hash"] = updates[
                    "password_hash"
                ]

            _raise_user_validation_error(
                updated["email"],
                updated["password_hash"],
            )

            duplicate = self.get_user_by_email(
                updated["email"]
            )

            if (
                duplicate is not None
                and duplicate["id"] != str(user_id)
            ):
                raise ValueError(
                    "A user with that email already exists."
                )

            self._users[index] = updated

            return deepcopy(updated)

        return None


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

        self.database = self.client[database_name]

        self.collection = self.database[
            ENTRIES_COLLECTION
        ]

        self.users_collection = self.database[
            USERS_COLLECTION
        ]

        self.goals_collection = self.database[
            GOALS_COLLECTION
        ]

    def ping(self) -> None:
        self.client.admin.command("ping")
        self.ensure_indexes()

    def ensure_indexes(self) -> None:
        for index in ENTRY_INDEXES:
            self.collection.create_index(
                index["keys"],
                name=index["name"],
            )

        for index in USER_INDEXES:
            self.users_collection.create_index(
                index["keys"],
                name=index["name"],
                unique=index.get("unique", False),
            )

        for index in GOAL_INDEXES:
            self.goals_collection.create_index(
                index["keys"],
                name=index["name"],
                unique=index.get("unique", False),
            )

    def create_entry(
        self,
        feature: str,
        user_id: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        _raise_entry_validation_error(
            feature,
            user_id,
            payload,
        )

        document = _entry_document(
            feature,
            user_id,
            payload,
        )

        result = self.collection.insert_one(document)
        document["_id"] = result.inserted_id

        return _serialize_document(document)

    def add_entry(
        self,
        feature: str,
        user_id: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        return self.create_entry(
            feature,
            user_id,
            payload,
        )

    def get_entry(
        self,
        entry_id: str,
        feature: str,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        object_id = _to_object_id(entry_id)

        if object_id is None:
            return None

        document = self.collection.find_one(
            {
                "_id": object_id,
                "feature": feature,
                "user_id": user_id,
            }
        )

        if document is None:
            return None

        return _serialize_document(document)

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
            .limit(_limit_value(limit))
        )

        return [
            _serialize_document(document)
            for document in documents
        ]

    def list_entries_in_range(
        self,
        feature: str,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {
            "feature": feature,
            "user_id": user_id,
        }

        date_bounds: Dict[str, str] = {}

        if start_date is not None:
            date_bounds["$gte"] = start_date

        if end_date is not None:
            date_bounds["$lte"] = end_date

        if date_bounds:
            query["date"] = date_bounds

        documents = self.collection.find(query).sort(
            [
                ("date", 1),
                ("created_at", 1),
            ]
        )

        return [
            _serialize_document(document)
            for document in documents
        ]

    def delete_entry(
        self,
        entry_id: str,
        feature: str,
        user_id: str,
    ) -> bool:
        object_id = _to_object_id(entry_id)

        if object_id is None:
            return False

        result = self.collection.delete_one(
            {
                "_id": object_id,
                "feature": feature,
                "user_id": user_id,
            }
        )

        return result.deleted_count == 1

    def get_water_goal(
        self,
        user_id: str,
    ) -> Optional[int]:
        document = self.goals_collection.find_one(
            {"user_id": user_id}
        )

        if document is None:
            return None

        return document["water_goal_oz"]

    def set_water_goal(
        self,
        user_id: str,
        water_goal_oz: int,
    ) -> int:
        document = _goal_document(
            user_id,
            water_goal_oz,
        )

        _raise_goal_validation_error(document)

        self.goals_collection.update_one(
            {"user_id": user_id},
            {"$set": document},
            upsert=True,
        )

        return water_goal_oz

    def update_entry(
        self,
        entry_id: str,
        feature: str,
        user_id: str,
        payload: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        _raise_entry_validation_error(
            feature,
            user_id,
            payload,
        )

        object_id = _to_object_id(entry_id)

        if object_id is None:
            return None

        query = {
            "_id": object_id,
            "feature": feature,
            "user_id": user_id,
        }

        current = self.collection.find_one(query)

        if current is None:
            return None

        updated = deepcopy(current)
        updated["date"] = payload["date"]
        updated["data"] = deepcopy(payload)

        _validate_entry_document(updated)

        self.collection.update_one(
            query,
            {
                "$set": {
                    "date": payload["date"],
                    "data": deepcopy(payload),
                }
            },
        )

        return _serialize_document(updated)

    def create_user(
        self,
        email: str,
        password_hash: str,
    ) -> Dict[str, Any]:
        _raise_user_validation_error(
            email,
            password_hash,
        )

        document = _user_document(
            email,
            password_hash,
        )

        result = self.users_collection.insert_one(document)
        document["_id"] = result.inserted_id

        return _serialize_document(document)

    def get_user(
        self,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        object_id = _to_object_id(user_id)

        if object_id is None:
            return None

        document = self.users_collection.find_one(
            {"_id": object_id}
        )

        if document is None:
            return None

        return _serialize_document(document)

    def get_user_by_email(
        self,
        email: str,
    ) -> Optional[Dict[str, Any]]:
        normalized_email = _normalize_email(email)

        document = self.users_collection.find_one(
            {"email": normalized_email}
        )

        if document is None:
            return None

        return _serialize_document(document)

    def update_user(
        self,
        user_id: str,
        updates: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(updates, dict):
            raise ValueError(
                "User updates must be an object."
            )

        allowed_fields = {
            "email",
            "password_hash",
        }

        unknown_fields = set(updates) - allowed_fields

        if unknown_fields:
            raise ValueError(
                "User updates contain unsupported fields: {}.".format(
                    ", ".join(sorted(unknown_fields))
                )
            )

        object_id = _to_object_id(user_id)

        if object_id is None:
            return None

        current = self.users_collection.find_one(
            {"_id": object_id}
        )

        if current is None:
            return None

        updated = deepcopy(current)

        if "email" in updates:
            updated["email"] = _normalize_email(
                updates["email"]
            )

        if "password_hash" in updates:
            updated["password_hash"] = updates[
                "password_hash"
            ]

        _raise_user_validation_error(
            updated["email"],
            updated["password_hash"],
        )

        changes = {
            field: updated[field]
            for field in allowed_fields
            if field in updates
        }

        if not changes:
            return _serialize_document(updated)

        self.users_collection.update_one(
            {"_id": object_id},
            {"$set": changes},
        )

        return _serialize_document(updated)
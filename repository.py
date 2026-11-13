from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from groups import (
    MAX_GROUP_MEMBERS,
    generate_join_code,
    normalize_join_code,
)
from schema import (
    ENTRIES_COLLECTION,
    ENTRY_INDEXES,
    GOAL_INDEXES,
    GOALS_COLLECTION,
    GROUP_INDEXES,
    GROUPS_COLLECTION,
    JOIN_FAILURE_INDEXES,
    JOIN_FAILURES_COLLECTION,
    USER_INDEXES,
    USERS_COLLECTION,
    validate_entry_document_shape,
    validate_goal_document_shape,
    validate_group_document_shape,
    validate_user_document_shape,
)

# How many join codes to try before giving up on creating a group.
JOIN_CODE_ATTEMPTS = 10


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


def _normalize_display_name(display_name: Any) -> Any:
    if isinstance(display_name, str):
        return display_name.strip()

    return display_name


def _user_document(
    email: str,
    password_hash: str,
    created_at: Optional[str] = None,
    display_name: Optional[str] = None,
) -> Dict[str, Any]:
    document = {
        "email": _normalize_email(email),
        "password_hash": password_hash,
        "created_at": created_at or _utc_now(),
    }

    if display_name is not None:
        document["display_name"] = _normalize_display_name(display_name)

    return document


def _group_document(
    name: Any,
    join_code: str,
    creator_id: str,
) -> Dict[str, Any]:
    """Build a validated group document or raise ValueError."""

    document = {
        "name": name.strip() if isinstance(name, str) else name,
        "join_code": join_code,
        "member_ids": [creator_id],
        "created_by": creator_id,
        "created_at": _utc_now(),
    }

    errors = validate_group_document_shape(document)

    if errors:
        raise ValueError(
            "Invalid group data: {}".format(
                " ".join(errors)
            )
        )

    return document


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
    display_name: Optional[str] = None,
) -> List[str]:

    document = _user_document(
        email,
        password_hash,
        display_name=display_name,
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
    display_name: Optional[str] = None,
) -> None:
    errors = validate_user_data(
        email,
        password_hash,
        display_name,
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
        self._groups: List[Dict[str, Any]] = []
        self._join_failures: List[Dict[str, Any]] = []

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
        display_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        _raise_user_validation_error(
            email,
            password_hash,
            display_name,
        )

        normalized_email = _normalize_email(email)

        if self.get_user_by_email(normalized_email):
            raise ValueError(
                "A user with that email already exists."
            )

        user = _user_document(
            email,
            password_hash,
            display_name=display_name,
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
            "display_name",
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

            if "display_name" in updates:
                updated["display_name"] = _normalize_display_name(
                    updates["display_name"]
                )

            _raise_user_validation_error(
                updated["email"],
                updated["password_hash"],
                updated.get("display_name"),
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

    def create_group(
        self,
        name: str,
        creator_id: str,
        code_factory=generate_join_code,
    ) -> Dict[str, Any]:
        _group_document(name, "pending", creator_id)

        for _ in range(JOIN_CODE_ATTEMPTS):
            join_code = normalize_join_code(code_factory())

            if self.get_group_by_code(join_code) is not None:
                continue

            group = _group_document(name, join_code, creator_id)
            group["id"] = str(uuid4())

            self._groups.append(deepcopy(group))

            return deepcopy(group)

        raise RuntimeError(
            "Could not generate an unused join code."
        )

    def get_group(
        self,
        group_id: str,
    ) -> Optional[Dict[str, Any]]:
        for group in self._groups:
            if group["id"] == str(group_id):
                return deepcopy(group)

        return None

    def get_group_by_code(
        self,
        code: str,
    ) -> Optional[Dict[str, Any]]:
        join_code = normalize_join_code(code)

        for group in self._groups:
            if group["join_code"] == join_code:
                return deepcopy(group)

        return None

    def list_groups_for_user(
        self,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        groups = [
            group
            for group in self._groups
            if user_id in group["member_ids"]
        ]

        groups.sort(key=lambda group: group["created_at"])

        return deepcopy(groups)

    def add_group_member(
        self,
        group_id: str,
        user_id: str,
    ) -> str:
        for group in self._groups:
            if group["id"] != str(group_id):
                continue

            if user_id in group["member_ids"]:
                return "already_member"

            if len(group["member_ids"]) >= MAX_GROUP_MEMBERS:
                return "full"

            group["member_ids"].append(user_id)

            return "joined"

        return "not_found"

    def remove_group_member(
        self,
        group_id: str,
        user_id: str,
    ) -> bool:
        for index, group in enumerate(self._groups):
            if group["id"] != str(group_id):
                continue

            if user_id not in group["member_ids"]:
                return False

            group["member_ids"].remove(user_id)

            # A group nobody belongs to can never be seen again.
            if not group["member_ids"]:
                del self._groups[index]

            return True

        return False

    def list_users(
        self,
        user_ids: List[str],
    ) -> List[Dict[str, Any]]:
        wanted = {str(user_id) for user_id in user_ids}

        return [
            deepcopy(user)
            for user in self._users
            if user["id"] in wanted
        ]

    def list_entries_for_users_in_range(
        self,
        feature: str,
        user_ids: List[str],
        start_date: str,
        end_date: str,
    ) -> List[Dict[str, Any]]:
        wanted = set(user_ids)

        return [
            deepcopy(entry)
            for entry in self._entries
            if entry["feature"] == feature
            and entry["user_id"] in wanted
            and _in_date_range(
                entry["date"],
                start_date,
                end_date,
            )
        ]


    def record_join_failure(
        self,
        user_id: str,
        at: datetime,
    ) -> None:
        self._join_failures.append({"user_id": user_id, "at": at})

    def count_join_failures_since(
        self,
        user_id: str,
        since: datetime,
    ) -> int:
        return sum(
            1
            for failure in self._join_failures
            if failure["user_id"] == user_id and failure["at"] >= since
        )


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

        self.groups_collection = self.database[
            GROUPS_COLLECTION
        ]

        self.join_failures_collection = self.database[
            JOIN_FAILURES_COLLECTION
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

        for index in GROUP_INDEXES:
            self.groups_collection.create_index(
                index["keys"],
                name=index["name"],
                unique=index.get("unique", False),
            )

        for index in JOIN_FAILURE_INDEXES:
            options = {"name": index["name"]}

            if "expire_after_seconds" in index:
                options["expireAfterSeconds"] = index["expire_after_seconds"]

            self.join_failures_collection.create_index(
                index["keys"],
                **options,
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
        display_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        _raise_user_validation_error(
            email,
            password_hash,
            display_name,
        )

        document = _user_document(
            email,
            password_hash,
            display_name=display_name,
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
            "display_name",
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

        if "display_name" in updates:
            updated["display_name"] = _normalize_display_name(
                updates["display_name"]
            )

        _raise_user_validation_error(
            updated["email"],
            updated["password_hash"],
            updated.get("display_name"),
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

    def create_group(
        self,
        name: str,
        creator_id: str,
        code_factory=generate_join_code,
    ) -> Dict[str, Any]:
        from pymongo.errors import DuplicateKeyError

        _group_document(name, "pending", creator_id)

        for _ in range(JOIN_CODE_ATTEMPTS):
            document = _group_document(
                name,
                normalize_join_code(code_factory()),
                creator_id,
            )

            try:
                # The unique join_code index rejects a code already in use.
                result = self.groups_collection.insert_one(document)
            except DuplicateKeyError:
                continue

            document["_id"] = result.inserted_id

            return _serialize_document(document)

        raise RuntimeError(
            "Could not generate an unused join code."
        )

    def get_group(
        self,
        group_id: str,
    ) -> Optional[Dict[str, Any]]:
        object_id = _to_object_id(group_id)

        if object_id is None:
            return None

        document = self.groups_collection.find_one(
            {"_id": object_id}
        )

        if document is None:
            return None

        return _serialize_document(document)

    def get_group_by_code(
        self,
        code: str,
    ) -> Optional[Dict[str, Any]]:
        document = self.groups_collection.find_one(
            {"join_code": normalize_join_code(code)}
        )

        if document is None:
            return None

        return _serialize_document(document)

    def list_groups_for_user(
        self,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        documents = self.groups_collection.find(
            {"member_ids": user_id}
        ).sort(
            [
                ("created_at", 1),
                ("_id", 1),
            ]
        )

        return [
            _serialize_document(document)
            for document in documents
        ]

    def add_group_member(
        self,
        group_id: str,
        user_id: str,
    ) -> str:
        object_id = _to_object_id(group_id)

        if object_id is None:
            return "not_found"

        # One conditional update, so two people joining at once cannot
        # push the group past its limit or add the same member twice.
        result = self.groups_collection.update_one(
            {
                "_id": object_id,
                "member_ids": {"$ne": user_id},
                "member_ids.{}".format(MAX_GROUP_MEMBERS - 1): {
                    "$exists": False
                },
            },
            {"$addToSet": {"member_ids": user_id}},
        )

        if result.modified_count:
            return "joined"

        group = self.get_group(group_id)

        if group is None:
            return "not_found"

        if user_id in group["member_ids"]:
            return "already_member"

        return "full"

    def remove_group_member(
        self,
        group_id: str,
        user_id: str,
    ) -> bool:
        object_id = _to_object_id(group_id)

        if object_id is None:
            return False

        result = self.groups_collection.update_one(
            {
                "_id": object_id,
                "member_ids": user_id,
            },
            {"$pull": {"member_ids": user_id}},
        )

        if not result.modified_count:
            return False

        # A group nobody belongs to can never be seen again.
        self.groups_collection.delete_one(
            {
                "_id": object_id,
                "member_ids": {"$size": 0},
            }
        )

        return True

    def list_users(
        self,
        user_ids: List[str],
    ) -> List[Dict[str, Any]]:
        object_ids = [
            object_id
            for object_id in (
                _to_object_id(user_id)
                for user_id in user_ids
            )
            if object_id is not None
        ]

        if not object_ids:
            return []

        documents = self.users_collection.find(
            {"_id": {"$in": object_ids}}
        )

        return [
            _serialize_document(document)
            for document in documents
        ]

    def list_entries_for_users_in_range(
        self,
        feature: str,
        user_ids: List[str],
        start_date: str,
        end_date: str,
    ) -> List[Dict[str, Any]]:
        if not user_ids:
            return []

        documents = self.collection.find(
            {
                "feature": feature,
                "user_id": {"$in": list(user_ids)},
                "date": {
                    "$gte": start_date,
                    "$lte": end_date,
                },
            }
        )

        return [
            _serialize_document(document)
            for document in documents
        ]

    def record_join_failure(
        self,
        user_id: str,
        at: datetime,
    ) -> None:
        # Stored as a real date (not text) so the expiry index can use it.
        self.join_failures_collection.insert_one(
            {"user_id": user_id, "at": at}
        )

    def count_join_failures_since(
        self,
        user_id: str,
        since: datetime,
    ) -> int:
        return self.join_failures_collection.count_documents(
            {
                "user_id": user_id,
                "at": {"$gte": since},
            }
        )

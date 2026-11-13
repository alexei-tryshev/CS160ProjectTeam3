"""Join codes and limits for step-competition groups."""

import secrets
from typing import Any


# Letters and digits with look-alikes (0 O 1 I L) removed, so a code
# read aloud or copied by hand is unambiguous.
JOIN_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
JOIN_CODE_LENGTH = 6

MAX_GROUP_MEMBERS = 50
MAX_GROUP_NAME_LENGTH = 40


def generate_join_code() -> str:
    return "".join(
        secrets.choice(JOIN_CODE_ALPHABET)
        for _ in range(JOIN_CODE_LENGTH)
    )


def normalize_join_code(raw: Any) -> str:
    if raw is None:
        return ""

    return str(raw).strip().upper()

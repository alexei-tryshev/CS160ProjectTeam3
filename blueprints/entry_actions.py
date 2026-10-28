"""Form helpers shared by the dedicated feature pages."""

from typing import Any, Dict, List, Optional

from flask import current_app, flash

from features import DEFAULT_USER_ID
from validation import validate_entry


def repository():
    return current_app.extensions["repository"]


def entry_form_values(entry: Dict[str, Any]) -> Dict[str, str]:
    values = {
        name: str(value)
        for name, value in entry["data"].items()
    }
    values["entry_id"] = entry["id"]

    return values


def load_entry_for_edit(
    feature: str,
    entry_id: str,
) -> Optional[Dict[str, Any]]:
    return repository().get_entry(
        entry_id,
        feature,
        DEFAULT_USER_ID,
    )


def save_entry_form(
    feature: str,
    form: Dict[str, str],
) -> List[str]:
    """Create or update an entry from a submitted form.

    A non-empty ``entry_id`` field means the form is editing an
    existing entry. Returns user-readable errors; empty on success.
    """

    payload, errors = validate_entry(feature, form)

    if errors:
        return errors

    entry_id = form.get("entry_id")

    try:
        if entry_id:
            updated = repository().update_entry(
                entry_id,
                feature,
                DEFAULT_USER_ID,
                payload,
            )

            if updated is None:
                return ["Entry not found."]

            flash("Entry updated.", "success")
        else:
            repository().create_entry(
                feature,
                DEFAULT_USER_ID,
                payload,
            )

            flash("Entry saved.", "success")
    except ValueError as exc:
        return [str(exc)]

    return []


def delete_entry_and_flash(feature: str, entry_id: str) -> None:
    deleted = repository().delete_entry(
        entry_id,
        feature,
        DEFAULT_USER_ID,
    )

    if deleted:
        flash("Entry deleted.", "success")
    else:
        flash("Entry not found.", "error")

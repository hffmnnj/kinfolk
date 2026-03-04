"""Voice-driven task management intent handler.

Routes task intents (add, query, complete) to the tasks database
and returns TTS-friendly response strings.  Supports named lists
(shopping, to-do, custom) via the ``list_id`` column on the Task model.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

from sqlalchemy.orm import Session

from app.models.task import Task
from app.schemas.intent import Intent

LOGGER = logging.getLogger(__name__)

# Intent names from sentences.ini / NLU
_ADD_TASK = "add_task"
_GET_TASKS = "get_tasks"
_COMPLETE_TASK = "complete_task"

# Normalisation map: spoken list names → canonical list_id values
_LIST_ALIASES: dict[str, str] = {
    "shopping": "shopping",
    "to-do": "todo",
    "to do": "todo",
    "todo": "todo",
    "grocery": "shopping",
    "groceries": "shopping",
}

# Human-friendly labels for TTS output
_LIST_LABELS: dict[str, str] = {
    "shopping": "shopping",
    "todo": "to-do",
}


def _get_slot(intent: Intent, name: str) -> Optional[str]:
    """Extract a named slot value from an intent."""
    for slot in intent.slots:
        if slot.name == name:
            return slot.value.strip() if slot.value else None
    return None


def _normalise_list_name(raw: Optional[str]) -> str:
    """Map a spoken list name to a canonical ``list_id``."""
    if not raw:
        return "todo"
    key = raw.strip().lower()
    return _LIST_ALIASES.get(key, key)


def _list_label(list_id: str) -> str:
    """Return a TTS-friendly label for a list_id."""
    return _LIST_LABELS.get(list_id, list_id)


class TaskIntentHandler:
    """Handle task-related voice intents."""

    def __init__(self, db_factory: Callable[[], Session]) -> None:
        self._db_factory = db_factory

    async def handle(self, intent: Intent) -> str:
        """Route to add/query/complete based on intent name."""
        if intent.name == _ADD_TASK:
            return self._handle_add_task(intent)
        if intent.name == _GET_TASKS:
            return self._handle_get_tasks(intent)
        if intent.name == _COMPLETE_TASK:
            return self._handle_complete_task(intent)

        return "I'm not sure how to handle that task request."

    def _handle_add_task(self, intent: Intent) -> str:
        """Parse slots and create a task on the named list."""
        item = _get_slot(intent, "item")
        if not item:
            return "I need to know what to add to your list."

        list_name_raw = _get_slot(intent, "list_name")
        list_id = _normalise_list_name(list_name_raw)
        label = _list_label(list_id)

        db: Session = self._db_factory()
        try:
            task = Task(title=item, list_id=list_id)
            db.add(task)
            db.commit()
        except Exception:
            LOGGER.exception("Failed to add task '%s'", item)
            db.rollback()
            return f"Sorry, I couldn't add {item} to your {label} list."
        finally:
            db.close()

        return f"Added {item} to your {label} list."

    def _handle_get_tasks(self, intent: Intent) -> str:
        """Query incomplete tasks on a named list."""
        list_name_raw = _get_slot(intent, "list_name")
        list_id = _normalise_list_name(list_name_raw)
        label = _list_label(list_id)

        db: Session = self._db_factory()
        try:
            tasks = (
                db.query(Task)
                .filter(Task.list_id == list_id, Task.completed.is_(False))
                .all()
            )
        finally:
            db.close()

        if not tasks:
            return f"Your {label} list is empty."

        count = len(tasks)
        noun = "item" if count == 1 else "items"
        titles = ", ".join(t.title for t in tasks)
        return f"You have {count} {noun} on your {label} list: {titles}."

    def _handle_complete_task(self, intent: Intent) -> str:
        """Mark a task as completed by fuzzy title match."""
        item = _get_slot(intent, "item")
        if not item:
            return "Which task would you like to mark as done?"

        search_term = item.lower()

        db: Session = self._db_factory()
        try:
            incomplete = db.query(Task).filter(Task.completed.is_(False)).all()

            match: Optional[Task] = None
            for task in incomplete:
                if search_term in task.title.lower():
                    match = task
                    break

            if match is None:
                return f"I couldn't find an incomplete task matching '{item}'."

            match.completed = True
            db.commit()
        except Exception:
            LOGGER.exception("Failed to complete task '%s'", item)
            db.rollback()
            return f"Sorry, I couldn't mark {item} as done."
        finally:
            db.close()

        return f"Done! I've marked {match.title} as complete."

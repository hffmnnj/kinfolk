"""Tests for voice-driven task management intent handler."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.models.task import Task
from app.schemas.intent import Intent, IntentSlot
from app.services.intent_handlers.task_handler import (
    TaskIntentHandler,
    _normalise_list_name,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _intent(name: str, slots: dict[str, str] | None = None) -> Intent:
    """Shorthand intent builder."""
    slot_list = [IntentSlot(name=k, value=v) for k, v in (slots or {}).items()]
    return Intent(name=name, slots=slot_list, confidence=0.95)


def _make_handler(tasks: list[Task] | None = None):
    """Build a TaskIntentHandler backed by a mocked DB session.

    Returns ``(handler, mock_session)`` so tests can inspect DB calls.
    """
    existing = list(tasks or [])

    mock_session = MagicMock()

    # query().filter().all() returns the task list
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_filter.all.return_value = existing
    mock_query.filter.return_value = mock_filter
    mock_session.query.return_value = mock_query

    def factory():
        return mock_session

    handler = TaskIntentHandler(db_factory=factory)
    return handler, mock_session


# ---------------------------------------------------------------------------
# Normalise list name
# ---------------------------------------------------------------------------


class TestNormaliseListName:
    """Verify spoken list names map to canonical list_id values."""

    def test_shopping(self):
        assert _normalise_list_name("shopping") == "shopping"

    def test_todo_variants(self):
        assert _normalise_list_name("to-do") == "todo"
        assert _normalise_list_name("to do") == "todo"
        assert _normalise_list_name("todo") == "todo"

    def test_grocery_alias(self):
        assert _normalise_list_name("grocery") == "shopping"
        assert _normalise_list_name("groceries") == "shopping"

    def test_custom_list_passes_through(self):
        assert _normalise_list_name("birthday") == "birthday"

    def test_none_defaults_to_todo(self):
        assert _normalise_list_name(None) == "todo"

    def test_empty_defaults_to_todo(self):
        assert _normalise_list_name("") == "todo"


# ---------------------------------------------------------------------------
# Add task
# ---------------------------------------------------------------------------


class TestHandleAddTask:
    """Test adding tasks via voice."""

    @pytest.mark.asyncio
    async def test_add_item_to_shopping_list(self):
        handler, mock_session = _make_handler()

        intent = _intent("add_task", {"item": "milk", "list_name": "shopping"})
        response = await handler.handle(intent)

        mock_session.add.assert_called_once()
        added_task: Task = mock_session.add.call_args[0][0]
        assert added_task.title == "milk"
        assert added_task.list_id == "shopping"
        mock_session.commit.assert_called_once()

        assert "milk" in response
        assert "shopping" in response

    @pytest.mark.asyncio
    async def test_add_item_to_todo_list(self):
        handler, mock_session = _make_handler()

        intent = _intent(
            "add_task",
            {"item": "call doctor", "list_name": "to-do"},
        )
        response = await handler.handle(intent)

        added_task: Task = mock_session.add.call_args[0][0]
        assert added_task.title == "call doctor"
        assert added_task.list_id == "todo"
        assert "call doctor" in response
        assert "to-do" in response

    @pytest.mark.asyncio
    async def test_add_item_default_list(self):
        handler, mock_session = _make_handler()

        intent = _intent("add_task", {"item": "buy flowers"})
        response = await handler.handle(intent)

        added_task: Task = mock_session.add.call_args[0][0]
        assert added_task.list_id == "todo"
        assert "buy flowers" in response

    @pytest.mark.asyncio
    async def test_add_missing_item_returns_prompt(self):
        handler, mock_session = _make_handler()

        intent = _intent("add_task", {"list_name": "shopping"})
        response = await handler.handle(intent)

        mock_session.add.assert_not_called()
        assert "need" in response.lower()

    @pytest.mark.asyncio
    async def test_add_db_error_returns_apology(self):
        handler, mock_session = _make_handler()
        mock_session.commit.side_effect = RuntimeError("DB error")

        intent = _intent("add_task", {"item": "eggs", "list_name": "shopping"})
        response = await handler.handle(intent)

        assert "sorry" in response.lower()
        mock_session.rollback.assert_called_once()


# ---------------------------------------------------------------------------
# Query tasks
# ---------------------------------------------------------------------------


class TestHandleGetTasks:
    """Test querying tasks via voice."""

    @pytest.mark.asyncio
    async def test_query_shopping_list_returns_spoken_list(self):
        tasks = [
            Task(title="milk", list_id="shopping", completed=False),
            Task(title="eggs", list_id="shopping", completed=False),
            Task(title="bread", list_id="shopping", completed=False),
        ]
        handler, _ = _make_handler(tasks)

        intent = _intent("get_tasks", {"list_name": "shopping"})
        response = await handler.handle(intent)

        assert "3 items" in response
        assert "milk" in response
        assert "eggs" in response
        assert "bread" in response
        assert "shopping" in response

    @pytest.mark.asyncio
    async def test_query_single_item_uses_singular(self):
        tasks = [Task(title="call doctor", list_id="todo", completed=False)]
        handler, _ = _make_handler(tasks)

        intent = _intent("get_tasks", {"list_name": "to-do"})
        response = await handler.handle(intent)

        assert "1 item" in response
        assert "call doctor" in response

    @pytest.mark.asyncio
    async def test_query_empty_list(self):
        handler, _ = _make_handler([])

        intent = _intent("get_tasks", {"list_name": "shopping"})
        response = await handler.handle(intent)

        assert "empty" in response.lower()
        assert "shopping" in response

    @pytest.mark.asyncio
    async def test_query_default_list(self):
        tasks = [Task(title="laundry", list_id="todo", completed=False)]
        handler, _ = _make_handler(tasks)

        intent = _intent("get_tasks")
        response = await handler.handle(intent)

        assert "to-do" in response
        assert "laundry" in response


# ---------------------------------------------------------------------------
# Complete task
# ---------------------------------------------------------------------------


class TestHandleCompleteTask:
    """Test completing tasks via voice with 2-step confirmation."""

    @pytest.mark.asyncio
    async def test_complete_asks_for_confirmation(self):
        task = Task(title="call doctor", list_id="todo", completed=False)
        handler, mock_session = _make_handler([task])

        intent = _intent("complete_task", {"item": "call doctor"})
        response = await handler.handle(intent)

        # Should NOT be completed yet
        assert task.completed is False
        assert "call doctor" in response
        assert "say yes to confirm" in response.lower()

    @pytest.mark.asyncio
    async def test_complete_confirmed_marks_done(self):
        task = Task(title="call doctor", list_id="todo", completed=False)
        handler, mock_session = _make_handler([task])

        # Mock merge to return the same task object
        mock_session.merge.return_value = task

        # Step 1: request completion → confirmation prompt
        await handler.handle(
            _intent("complete_task", {"item": "call doctor"}),
        )
        assert task.completed is False

        # Step 2: confirm with "yes"
        response = await handler.handle(
            _intent("complete_task", {"item": "yes"}),
        )

        assert task.completed is True
        mock_session.merge.assert_called_once()
        assert "call doctor" in response
        assert "complete" in response.lower() or "done" in response.lower()

    @pytest.mark.asyncio
    async def test_complete_confirm_variants(self):
        """Confirm words like 'yeah', 'confirm', 'sure' all work."""
        for word in ("yeah", "confirm", "sure", "yep", "do it"):
            task = Task(title="laundry", list_id="todo", completed=False)
            handler, mock_session = _make_handler([task])
            mock_session.merge.return_value = task

            await handler.handle(
                _intent("complete_task", {"item": "laundry"}),
            )
            response = await handler.handle(
                _intent("complete_task", {"item": word}),
            )

            assert task.completed is True, (
                f"Confirm word '{word}' did not trigger completion"
            )
            assert "complete" in response.lower() or "done" in response.lower()

    @pytest.mark.asyncio
    async def test_complete_partial_match_asks_confirmation(self):
        task = Task(title="call doctor smith", list_id="todo", completed=False)
        handler, mock_session = _make_handler([task])

        intent = _intent("complete_task", {"item": "call doctor"})
        response = await handler.handle(intent)

        assert task.completed is False
        assert "call doctor smith" in response
        assert "say yes to confirm" in response.lower()

    @pytest.mark.asyncio
    async def test_complete_new_target_replaces_pending(self):
        """A new complete intent while pending replaces the pending target."""
        task_a = Task(title="call doctor", list_id="todo", completed=False)
        task_b = Task(title="buy flowers", list_id="todo", completed=False)
        handler, mock_session = _make_handler([task_a, task_b])
        mock_session.merge.return_value = task_b

        # Request complete A
        await handler.handle(
            _intent("complete_task", {"item": "call doctor"}),
        )
        # Change mind — request complete B instead
        response = await handler.handle(
            _intent("complete_task", {"item": "buy flowers"}),
        )
        assert "buy flowers" in response
        assert "say yes to confirm" in response.lower()

        # Confirm → should complete B, not A
        response = await handler.handle(
            _intent("complete_task", {"item": "yes"}),
        )
        assert "buy flowers" in response
        assert task_b.completed is True
        assert task_a.completed is False

    @pytest.mark.asyncio
    async def test_complete_no_match(self):
        task = Task(title="buy groceries", list_id="shopping", completed=False)
        handler, _ = _make_handler([task])

        intent = _intent("complete_task", {"item": "call doctor"})
        response = await handler.handle(intent)

        assert task.completed is False
        assert "couldn't find" in response.lower()

    @pytest.mark.asyncio
    async def test_complete_missing_item_slot(self):
        handler, _ = _make_handler()

        intent = _intent("complete_task")
        response = await handler.handle(intent)

        assert "which task" in response.lower()

    @pytest.mark.asyncio
    async def test_complete_db_error_on_confirm_returns_apology(self):
        task = Task(title="call doctor", list_id="todo", completed=False)
        handler, mock_session = _make_handler([task])
        mock_session.merge.return_value = task
        mock_session.commit.side_effect = RuntimeError("DB error")

        # Step 1: request completion
        await handler.handle(
            _intent("complete_task", {"item": "call doctor"}),
        )
        # Step 2: confirm
        response = await handler.handle(
            _intent("complete_task", {"item": "yes"}),
        )

        assert "sorry" in response.lower()
        mock_session.rollback.assert_called_once()


# ---------------------------------------------------------------------------
# Unknown task intent
# ---------------------------------------------------------------------------


class TestUnknownTaskIntent:
    """Graceful handling of unrecognized task sub-intents."""

    @pytest.mark.asyncio
    async def test_unknown_task_intent(self):
        handler, _ = _make_handler()

        intent = _intent("some_unknown_task_thing")
        response = await handler.handle(intent)

        assert "not sure" in response.lower()


# ---------------------------------------------------------------------------
# Named list filtering
# ---------------------------------------------------------------------------


class TestNamedListFiltering:
    """Verify that list_name slot correctly filters tasks."""

    @pytest.mark.asyncio
    async def test_grocery_alias_maps_to_shopping(self):
        tasks = [Task(title="apples", list_id="shopping", completed=False)]
        handler, mock_session = _make_handler(tasks)

        intent = _intent("get_tasks", {"list_name": "grocery"})
        response = await handler.handle(intent)

        # Verify the filter was called with the canonical list_id
        mock_session.query.return_value.filter.assert_called()
        assert "apples" in response

    @pytest.mark.asyncio
    async def test_custom_list_name_passes_through(self):
        handler, mock_session = _make_handler()

        intent = _intent("add_task", {"item": "cake", "list_name": "birthday"})
        response = await handler.handle(intent)

        added_task: Task = mock_session.add.call_args[0][0]
        assert added_task.list_id == "birthday"
        assert "cake" in response

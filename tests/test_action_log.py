"""
test_action_log.py — Тесты модуля истории действий.
"""

import pytest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timedelta


class TestActionLog:
    """Тесты функций журнала действий."""

    def test_log_and_retrieve(self, tmp_path):
        from modules.action_log import log_action, get_actions

        db_path = tmp_path / "test_log.db"
        with patch('modules.action_log.DB_PATH', db_path):
            log_action("test", "Test action", "details", "ok", False)

            actions = get_actions(limit=10)
            assert len(actions) == 1
            assert actions[0]["type"] == "test"
            assert actions[0]["description"] == "Test action"

    def test_filter_by_type(self, tmp_path):
        from modules.action_log import log_action, get_actions

        db_path = tmp_path / "test_log.db"
        with patch('modules.action_log.DB_PATH', db_path):
            log_action("cleanup", "Clean 1")
            log_action("export", "Export 1")
            log_action("cleanup", "Clean 2")

            cleanup_actions = get_actions(action_type="cleanup")
            assert len(cleanup_actions) == 2

            export_actions = get_actions(action_type="export")
            assert len(export_actions) == 1

    def test_get_action_count(self, tmp_path):
        from modules.action_log import log_action, get_action_count

        db_path = tmp_path / "test_log.db"
        with patch('modules.action_log.DB_PATH', db_path):
            log_action("test", "Action 1")
            log_action("test", "Action 2")

            count = get_action_count()
            assert count == 2

    def test_clear_old_actions(self, tmp_path):
        from modules.action_log import log_action, get_actions, clear_old_actions

        db_path = tmp_path / "test_log.db"
        with patch('modules.action_log.DB_PATH', db_path):
            log_action("test", "Recent action")

            # Не удаляем ничего — все записи свежие
            clear_old_actions(days=30)
            actions = get_actions()
            assert len(actions) == 1

    def test_get_stats(self, tmp_path):
        from modules.action_log import log_action, get_stats

        db_path = tmp_path / "test_log.db"
        with patch('modules.action_log.DB_PATH', db_path):
            log_action("cleanup", "Clean 1")
            log_action("export", "Export 1")
            log_action("cleanup", "Clean 2")

            stats = get_stats()
            assert stats["total"] == 3
            assert stats["by_type"]["cleanup"] == 2
            assert stats["by_type"]["export"] == 1

    def test_undoable_flag(self, tmp_path):
        from modules.action_log import log_action, get_actions

        db_path = tmp_path / "test_log.db"
        with patch('modules.action_log.DB_PATH', db_path):
            log_action("test", "Undoable action", undoable=True)
            log_action("test", "Normal action", undoable=False)

            actions = get_actions()
            undoable = [a for a in actions if a["undoable"]]
            non_undoable = [a for a in actions if not a["undoable"]]

            assert len(undoable) == 1
            assert len(non_undoable) == 1

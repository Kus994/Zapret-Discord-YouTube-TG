"""
test_export.py — Тесты модуля экспорта данных.
"""

import pytest
import json
from pathlib import Path


class TestExport:
    """Тесты функций экспорта."""

    def test_export_processes_csv(self, tmp_path):
        from modules.export import export_processes_csv
        processes = [
            {"pid": 1, "name": "test.exe", "memory_mb": 10.5, "cpu_percent": 5.0, "disk_mb_s": 0.1, "user": "user", "status": "Running", "is_app": True},
            {"pid": 2, "name": "bg.exe", "memory_mb": 5.0, "cpu_percent": 1.0, "disk_mb_s": 0.0, "user": "user", "status": "Stopped", "is_app": False},
        ]

        filepath = str(tmp_path / "processes.csv")
        result = export_processes_csv(processes, filepath)

        assert result is True
        content = Path(filepath).read_text(encoding="utf-8-sig")
        assert "test.exe" in content
        assert "bg.exe" in content

    def test_export_processes_json(self, tmp_path):
        from modules.export import export_processes_json
        processes = [{"pid": 1, "name": "test.exe"}]

        filepath = str(tmp_path / "processes.json")
        result = export_processes_json(processes, filepath)

        assert result is True
        data = json.loads(Path(filepath).read_text(encoding="utf-8"))
        assert len(data) == 1

    def test_export_processes_html(self, tmp_path):
        from modules.export import export_processes_html
        processes = [{"pid": 1, "name": "test.exe", "memory_mb": 10, "cpu_percent": 5, "disk_mb_s": 0, "user": "user", "status": "Running", "is_app": True}]

        filepath = str(tmp_path / "processes.html")
        result = export_processes_html(processes, filepath)

        assert result is True
        content = Path(filepath).read_text(encoding="utf-8")
        assert "test.exe" in content
        assert "<table>" in content

    def test_export_timetrack_csv(self, tmp_path):
        from modules.export import export_timetrack_csv
        summary = {
            "date": "2026-07-08",
            "auto": [{"app": "chrome.exe", "seconds": 3600, "category": "neutral", "last_title": "Test"}],
            "manual": [{"name": "Work", "category": "Работа", "minutes": 30, "note": ""}],
        }

        filepath = str(tmp_path / "timetrack.csv")
        result = export_timetrack_csv(summary, filepath)

        assert result is True
        content = Path(filepath).read_text(encoding="utf-8-sig")
        assert "chrome.exe" in content
        assert "Work" in content

    def test_export_settings_json(self, tmp_path):
        from modules.export import export_settings_json
        config = {"game_mode": {"apps": []}, "start_minimized": False}

        filepath = str(tmp_path / "settings.json")
        result = export_settings_json(config, filepath)

        assert result is True
        data = json.loads(Path(filepath).read_text(encoding="utf-8"))
        assert "game_mode" in data

    def test_export_action_log_csv(self, tmp_path):
        from modules.export import export_action_log_csv
        actions = [
            {"timestamp": "2026-07-08T12:00:00", "type": "cleanup", "description": "Test cleanup", "status": "ok"},
        ]

        filepath = str(tmp_path / "actions.csv")
        result = export_action_log_csv(actions, filepath)

        assert result is True
        content = Path(filepath).read_text(encoding="utf-8-sig")
        assert "Test cleanup" in content

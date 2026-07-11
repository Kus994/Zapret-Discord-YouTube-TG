"""
test_timetrack.py — Тесты модуля хронометража.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch
from datetime import datetime


class TestTimeTrack:
    """Тесты функций хронометража."""

    def test_load_data_creates_default(self, tmp_path):
        from modules.timetrack import load_data, DEFAULT_DATA
        fake_file = tmp_path / "timetrack.json"
        with patch('modules.timetrack.DATA_FILE', fake_file):
            data = load_data()
            assert data["consent"] is False
            assert data["days"] == {}

    def test_load_data_merges_defaults(self, tmp_path):
        from modules.timetrack import load_data
        fake_file = tmp_path / "timetrack.json"
        fake_file.write_text(json.dumps({"consent": True}), encoding="utf-8")
        with patch('modules.timetrack.DATA_FILE', fake_file):
            data = load_data()
            assert data["consent"] is True
            assert "days" in data  # дефолт добавлен

    def test_save_and_load(self, tmp_path):
        from modules.timetrack import save_data, load_data
        fake_file = tmp_path / "timetrack.json"
        with patch('modules.timetrack.DATA_FILE', fake_file):
            test_data = {"consent": True, "app_categories": {}, "days": {"2026-01-01": {"auto": {}, "manual": []}}}
            save_data(test_data)
            loaded = load_data()
            assert loaded["consent"] is True

    def test_set_consent(self, tmp_path):
        from modules.timetrack import set_consent, has_consent
        fake_file = tmp_path / "timetrack.json"
        with patch('modules.timetrack.DATA_FILE', fake_file):
            set_consent(True)
            assert has_consent() is True
            set_consent(False)
            assert has_consent() is False

    def test_add_manual_entry(self, tmp_path):
        from modules.timetrack import add_manual_entry, load_data
        fake_file = tmp_path / "timetrack.json"
        with patch('modules.timetrack.DATA_FILE', fake_file):
            entry = add_manual_entry("Работа", "Тест", 30, "заметка")
            assert entry["name"] == "Тест"
            assert entry["minutes"] == 30
            assert entry["category"] == "Работа"

    def test_add_manual_entry_validation(self, tmp_path):
        from modules.timetrack import add_manual_entry
        fake_file = tmp_path / "timetrack.json"
        with patch('modules.timetrack.DATA_FILE', fake_file):
            with pytest.raises(ValueError):
                add_manual_entry("Работа", "", 30)
            with pytest.raises(ValueError):
                add_manual_entry("Работа", "Тест", 0)

    def test_delete_manual_entry(self, tmp_path):
        from modules.timetrack import add_manual_entry, delete_manual_entry, load_data
        fake_file = tmp_path / "timetrack.json"
        with patch('modules.timetrack.DATA_FILE', fake_file):
            entry = add_manual_entry("Работа", "Тест", 30)
            result = delete_manual_entry(entry["id"])
            assert result is True

    def test_set_app_category(self, tmp_path):
        from modules.timetrack import set_app_category, get_app_category
        fake_file = tmp_path / "timetrack.json"
        with patch('modules.timetrack.DATA_FILE', fake_file):
            set_app_category("chrome.exe", "distracting")
            cat = get_app_category("chrome.exe")
            assert cat == "distracting"

    def test_get_day_summary_empty(self, tmp_path):
        from modules.timetrack import get_day_summary
        fake_file = tmp_path / "timetrack.json"
        with patch('modules.timetrack.DATA_FILE', fake_file):
            summary = get_day_summary("2099-01-01")
            assert summary["total_auto_seconds"] == 0
            assert summary["total_manual_minutes"] == 0

    def test_format_hms(self):
        from modules.timetrack import format_hms
        assert format_hms(0) == "0 с"
        assert format_hms(65) == "1 мин 05 с"
        assert format_hms(3661) == "1 ч 01 мин"

    def test_format_minutes(self):
        from modules.timetrack import format_minutes
        assert format_minutes(0.5) == "30 с"
        assert format_minutes(60) == "1 ч 00 мин"

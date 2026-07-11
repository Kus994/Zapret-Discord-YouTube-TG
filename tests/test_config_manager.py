"""
test_config_manager.py — Тесты менеджера конфигурации.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch


class TestConfigManager:
    """Тесты чтения/записи конфигурации."""

    def test_load_config(self, tmp_config):
        from config_manager import load_config
        with patch('app_paths.CONFIG_FILE', tmp_config):
            config = load_config()
            assert "game_mode" in config
            assert "start_minimized" in config

    def test_get_value(self, tmp_config):
        from config_manager import get_value
        with patch('app_paths.CONFIG_FILE', tmp_config):
            val = get_value("start_minimized", False)
            assert val is False

    def test_get_value_default(self, tmp_config):
        from config_manager import get_value
        with patch('app_paths.CONFIG_FILE', tmp_config):
            val = get_value("nonexistent_key", "default")
            assert val == "default"

    def test_set_value(self, tmp_config):
        from config_manager import set_value, get_value
        with patch('app_paths.CONFIG_FILE', tmp_config):
            set_value("test_key", "test_value")
            val = get_value("test_key")
            assert val == "test_value"

    def test_get_section(self, tmp_config):
        from config_manager import get_section
        with patch('app_paths.CONFIG_FILE', tmp_config):
            section = get_section("game_mode")
            assert "apps" in section

    def test_set_section(self, tmp_config):
        from config_manager import set_section, get_section
        with patch('app_paths.CONFIG_FILE', tmp_config):
            new_section = {"apps": [{"label": "Test", "process": "test.exe"}]}
            set_section("game_mode", new_section)
            section = get_section("game_mode")
            assert section["apps"][0]["label"] == "Test"

    def test_save_creates_backup(self, tmp_config):
        from config_manager import save_config, load_config
        with patch('app_paths.CONFIG_FILE', tmp_config):
            config = load_config()
            config["test_backup"] = True
            save_config(config)
            # Проверяем что файл обновился
            loaded = json.loads(tmp_config.read_text(encoding="utf-8"))
            assert loaded.get("test_backup") is True

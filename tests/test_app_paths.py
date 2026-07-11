"""
test_app_paths.py — Тесты модуля путей приложения.
"""

import pytest
from pathlib import Path


class TestAppPaths:
    """Тесты констант путей."""

    def test_base_dir_exists(self):
        from app_paths import BASE_DIR
        assert BASE_DIR.exists()
        assert BASE_DIR.is_dir()

    def test_data_dir(self):
        from app_paths import DATA_DIR
        assert isinstance(DATA_DIR, Path)

    def test_config_file(self):
        from app_paths import CONFIG_FILE
        assert isinstance(CONFIG_FILE, Path)
        assert CONFIG_FILE.suffix == ".json"

    def test_assets_dir(self):
        from app_paths import ASSETS_DIR
        assert isinstance(ASSETS_DIR, Path)

    def test_icon_file(self):
        from app_paths import ICON_FILE
        assert isinstance(ICON_FILE, Path)

    def test_bg_file(self):
        from app_paths import BG_FILE
        assert isinstance(BG_FILE, Path)

    def test_ensure_config(self):
        from app_paths import ensure_config, CONFIG_FILE
        # ensure_config не должен падать
        ensure_config()
        # Конфиг должен существовать или быть создан

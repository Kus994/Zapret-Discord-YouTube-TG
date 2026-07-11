"""
conftest.py — Общие фикстуры для тестов KUS Pro.
"""

import sys
import os
import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Добавляем корень проекта в sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def tmp_config(tmp_path):
    """Создаёт временную конфигурацию для тестов."""
    config = {
        "game_mode": {
            "apps": [
                {"label": "TestApp", "process": "test.exe", "path": "", "enabled": True}
            ],
            "disable_transparency": True,
            "enable_taskbar_autohide": True,
            "auto_return_enabled": False,
            "auto_return_minutes": 60,
            "hotkey": ""
        },
        "autostart_zapret": False,
        "autostart_tg_proxy": False,
        "tg_proxy_port": 8080,
        "start_minimized": False,
        "auto_update_enabled": True,
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return config_file


@pytest.fixture
def tmp_timetrack(tmp_path):
    """Создаёт временный файл данных хронометража."""
    data = {
        "consent": False,
        "app_categories": {},
        "days": {}
    }
    tt_file = tmp_path / "timetrack_data.json"
    tt_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return tt_file


@pytest.fixture
def mock_psutil():
    """Мокает psutil для тестов, не требующих реальных данных системы."""
    with patch("psutil.cpu_percent", return_value=50.0), \
         patch("psutil.cpu_count", return_value=8), \
         patch("psutil.virtual_memory") as mock_vm, \
         patch("psutil.disk_partitions", return_value=[]), \
         patch("psutil.net_io_counters") as mock_net:
        
        mock_vm.return_value = MagicMock(
            percent=65.0, total=16 * 1024**3, available=5.6 * 1024**3
        )
        mock_net.return_value = MagicMock(bytes_recv=1000000, bytes_sent=500000)
        yield


@pytest.fixture
def mock_winreg():
    """Мокает winreg для тестов реестра."""
    mock_key = MagicMock()
    mock_key.__enter__ = MagicMock(return_value=mock_key)
    mock_key.__exit__ = MagicMock(return_value=False)
    mock_key.__iter__ = MagicMock(return_value=iter([]))
    return mock_key


@pytest.fixture
def sample_cleanup_log():
    """Фикстура для лог-функции очистки."""
    logs = []
    def log_func(msg, level="INFO"):
        logs.append((msg, level))
    return log_func, logs


@pytest.fixture
def sample_progress():
    """Фикстура для прогресс-функции."""
    values = []
    def progress_func(value):
        values.append(value)
    return progress_func, values

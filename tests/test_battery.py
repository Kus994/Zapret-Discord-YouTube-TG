"""
test_battery.py — Тесты модуля мониторинга батареи.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestBattery:
    """Тесты функций мониторинга батареи."""

    @patch('modules.battery.psutil')
    def test_get_battery_info_no_battery(self, mock_psutil):
        mock_psutil.sensors_battery.return_value = None

        from modules.battery import get_battery_info
        info = get_battery_info()

        assert info["status"] == "not present"
        assert info["percent"] == 0

    @patch('modules.battery.psutil')
    def test_get_battery_info_charging(self, mock_psutil):
        bat = MagicMock()
        bat.percent = 75
        bat.secsleft = 3600
        mock_psutil.sensors_battery.return_value = bat
        mock_psutil.POWER_TIME_UNLIMITED = -2
        mock_psutil.POWER_TIME_UNKNOWN = -1

        from modules.battery import get_battery_info
        info = get_battery_info()

        assert info["percent"] == 75
        assert info["status"] == "charging"
        assert info["time_left_sec"] == 3600

    @patch('modules.battery.psutil')
    def test_get_battery_info_discharging(self, mock_psutil):
        bat = MagicMock()
        bat.percent = 30
        bat.secsleft = 1800
        mock_psutil.sensors_battery.return_value = bat
        mock_psutil.POWER_TIME_UNLIMITED = -2
        mock_psutil.POWER_TIME_UNKNOWN = -1

        from modules.battery import get_battery_info
        info = get_battery_info()

        assert info["status"] == "discharging"

    def test_empty_battery(self):
        from modules.battery import _empty_battery
        info = _empty_battery()
        assert info["status"] == "not present"
        assert info["percent"] == 0
        assert info["power_plugged"] is False


class TestBatteryMonitor:
    """Тесты класса BatteryMonitor."""

    def test_init(self):
        from modules.battery import BatteryMonitor
        monitor = BatteryMonitor(interval=30, max_history=100)
        assert monitor.interval == 30
        assert monitor.max_history == 100

    @patch('modules.battery.get_battery_info')
    def test_get_history(self, mock_info):
        mock_info.return_value = {"percent": 50, "status": "discharging"}

        from modules.battery import BatteryMonitor
        monitor = BatteryMonitor(interval=1)
        history = monitor.get_history()
        assert isinstance(history, list)

    @patch('modules.battery.get_battery_info')
    def test_estimate_empty_time_no_data(self, mock_info):
        mock_info.return_value = {"percent": 50, "status": "discharging"}

        from modules.battery import BatteryMonitor
        monitor = BatteryMonitor()
        result = monitor.estimate_empty_time()
        assert "Недостаточно данных" in result

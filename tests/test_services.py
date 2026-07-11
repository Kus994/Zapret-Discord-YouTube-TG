"""
test_services.py — Тесты модуля управления службами.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestServices:
    """Тесты функций управления службами."""

    def test_is_critical(self):
        from modules.services import is_critical
        assert is_critical("rpcss") is True
        assert is_critical("lsass") is True
        assert is_critical("wuauserv") is True
        assert is_critical("notepad") is False

    @patch('modules.services._run_sc')
    def test_list_services(self, mock_sc):
        mock_sc.return_value = (
            """SERVICE_NAME: wuauserv
DISPLAY_NAME: Windows Update
STATE: 4  RUNNING
PID: 1234
SERVICE_NAME: spooler
DISPLAY_NAME: Print Spooler
STATE: 1  STOPPED
PID: 0""",
            0,
        )

        from modules.services import list_services
        services = list_services()

        assert len(services) == 2
        assert services[0]["name"] == "wuauserv"
        assert services[0]["status"] == "Running"
        assert services[1]["name"] == "spooler"
        assert services[1]["status"] == "Stopped"

    @patch('modules.services._run_sc')
    def test_get_start_type(self, mock_sc):
        mock_sc.return_value = ("START_TYPE : 2   AUTO_START", 0)

        from modules.services import _get_start_type
        result = _get_start_type("wuauserv")
        assert result == "Auto"

    @patch('modules.services._run_sc')
    def test_start_service(self, mock_sc):
        mock_sc.return_value = ("[SC] StartService SUCCESS", 0)

        from modules.services import start_service
        log = lambda msg, lvl="INFO": None

        result = start_service("spooler", log)
        assert result is True

    @patch('modules.services._run_sc')
    def test_stop_service(self, mock_sc):
        mock_sc.return_value = ("[SC] ControlService SUCCESS", 0)

        from modules.services import stop_service
        log = lambda msg, lvl="INFO": None

        result = stop_service("spooler", log)
        assert result is True

    def test_critical_service_blocked(self):
        from modules.services import start_service
        log = lambda msg, lvl="INFO": None

        result = start_service("lsass", log)
        assert result is False

    @patch('modules.services._run_sc')
    def test_search_services(self, mock_sc):
        mock_sc.return_value = (
            """SERVICE_NAME: wuauserv
DISPLAY_NAME: Windows Update
STATE: 4  RUNNING
PID: 1234""",
            0,
        )

        from modules.services import list_services, search_services
        services = list_services()
        results = search_services("update", services)
        assert len(results) >= 1

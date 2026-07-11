"""
test_processes.py — Тесты модуля процессов.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestProcesses:
    """Тесты функций управления процессами."""

    def test_is_protected_system(self):
        from modules.processes import is_protected
        assert is_protected(0, "System") is True
        assert is_protected(4, "System Idle Process") is True

    def test_is_protected_svchost(self):
        from modules.processes import is_protected
        assert is_protected(1234, "svchost.exe") is True

    def test_is_protected_normal(self):
        from modules.processes import is_protected
        assert is_protected(9999, "notepad.exe") is False

    def test_is_protected_empty_name(self):
        from modules.processes import is_protected
        assert is_protected(9999, "") is False

    @patch('modules.processes.psutil')
    def test_list_processes(self, mock_psutil):
        proc = MagicMock()
        proc.info = {
            "pid": 100,
            "name": "test.exe",
            "memory_info": MagicMock(rss=50 * 1024 * 1024),
            "create_time": 1000000,
        }
        proc.cpu_percent.return_value = 10.0
        proc.username.return_value = "TESTDOMAIN\\user"
        proc.status.return_value = "running"
        proc.io_counters.return_value = MagicMock(read_bytes=0, write_bytes=0)

        mock_psutil.process_iter.return_value = [proc]
        mock_psutil.STATUS_RUNNING = "running"
        mock_psutil.STATUS_SLEEPING = "sleeping"
        mock_psutil.STATUS_STOPPED = "stopped"

        from modules.processes import list_processes
        processes = list_processes()

        assert len(processes) == 1
        assert processes[0]["name"] == "test.exe"
        assert processes[0]["pid"] == 100

    @patch('modules.processes.psutil')
    def test_kill_process_by_name(self, mock_psutil):
        proc = MagicMock()
        proc.info = {"pid": 100, "name": "test.exe"}
        proc.name.return_value = "test.exe"
        proc.children.return_value = []

        mock_psutil.process_iter.return_value = [proc]

        from modules.processes import kill_process
        log = lambda msg: None
        progress = lambda p: None

        killed = kill_process("test.exe", log, progress)
        assert killed >= 0

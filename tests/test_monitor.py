"""
test_monitor.py — Тесты модуля мониторинга.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestMonitor:
    """Тесты функций мониторинга."""

    @patch('modules.monitor.psutil')
    def test_get_snapshot(self, mock_psutil):
        mock_psutil.cpu_percent.return_value = 50.0
        mock_psutil.cpu_count.return_value = 8

        vm = MagicMock()
        vm.percent = 65.0
        vm.total = 16 * 1024**3
        vm.available = 5.6 * 1024**3
        mock_psutil.virtual_memory.return_value = vm

        sw = MagicMock()
        sw.percent = 10.0
        sw.used = 1 * 1024**3
        sw.total = 10 * 1024**3
        mock_psutil.swap_memory.return_value = sw

        mock_psutil.disk_partitions.return_value = []
        mock_psutil.net_io_counters.return_value = MagicMock(bytes_recv=0, bytes_sent=0)

        from modules.monitor import get_snapshot
        snapshot = get_snapshot()

        assert "cpu_percent" in snapshot
        assert "ram_percent" in snapshot
        assert "disks" in snapshot

    @patch('modules.monitor.psutil')
    def test_get_top_processes(self, mock_psutil):
        mock_psutil.cpu_count.return_value = 4

        proc = MagicMock()
        proc.info = {"pid": 1, "name": "test.exe", "memory_info": MagicMock(rss=100 * 1024 * 1024)}
        proc.cpu_percent.return_value = 25.0

        mock_psutil.process_iter.return_value = [proc]

        from modules.monitor import get_top_processes
        result = get_top_processes(limit=5)

        assert "top_cpu" in result
        assert "top_mem" in result

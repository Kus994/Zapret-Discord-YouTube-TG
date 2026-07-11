"""
test_cleanup.py — Тесты модуля очистки системы.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestHumanSize:
    """Тесты функции форматирования размера."""

    def test_bytes(self):
        from modules.cleanup import human_size
        assert human_size(0) == "0.0 Б"
        assert human_size(512) == "512.0 Б"

    def test_kilobytes(self):
        from modules.cleanup import human_size
        result = human_size(1024)
        assert "КБ" in result

    def test_megabytes(self):
        from modules.cleanup import human_size
        result = human_size(1024 * 1024)
        assert "МБ" in result

    def test_gigabytes(self):
        from modules.cleanup import human_size
        result = human_size(1024 ** 3)
        assert "ГБ" in result

    def test_terabytes(self):
        from modules.cleanup import human_size
        result = human_size(1024 ** 4)
        assert "ТБ" in result


class TestSafeRemoveTree:
    """Тесты безопасного удаления дерева."""

    def test_removes_files(self, tmp_path):
        from modules.cleanup import _safe_remove_tree
        # Создаём тестовые файлы
        (tmp_path / "file1.txt").write_text("test")
        (tmp_path / "file2.txt").write_text("test2")
        sub = tmp_path / "subdir"
        sub.mkdir()
        (sub / "file3.txt").write_text("test3")

        log = lambda msg: None
        freed = _safe_remove_tree(tmp_path, log)

        assert freed > 0
        assert not list(tmp_path.iterdir())

    def test_handles_nonexistent(self, tmp_path):
        from modules.cleanup import _safe_remove_tree
        fake = tmp_path / "nonexistent"
        log = lambda msg: None
        freed = _safe_remove_tree(fake, log)
        assert freed == 0

    def test_handles_permission_error(self, tmp_path):
        from modules.cleanup import _safe_remove_tree
        # Создаём файл
        f = tmp_path / "locked.txt"
        f.write_text("test")

        log_msgs = []
        log = lambda msg: log_msgs.append(msg)

        # Мокаем unlink чтобы выбросить PermissionError
        with patch.object(Path, 'unlink', side_effect=PermissionError()):
            freed = _safe_remove_tree(tmp_path, log)

        # Должен продолжить работу несмотря на ошибку
        assert any("пропущено" in m for m in log_msgs)


class TestGetAllDrives:
    """Тесты получения списка дисков."""

    def test_returns_list(self):
        from modules.cleanup import _get_all_drives
        drives = _get_all_drives()
        assert isinstance(drives, list)

    def test_returns_path_objects(self):
        from modules.cleanup import _get_all_drives
        from pathlib import Path
        drives = _get_all_drives()
        for d in drives:
            assert isinstance(d, Path)


class TestDuplicateFinder:
    """Тесты поиска дублей файлов."""

    def test_finds_duplicates(self, tmp_path):
        from modules.cleanup import find_duplicate_files
        # Создаём два одинаковых файла
        content = "identical content for testing"
        (tmp_path / "file1.txt").write_text(content)
        (tmp_path / "file2.txt").write_text(content)
        # Разный файл
        (tmp_path / "file3.txt").write_text("different content")

        log = lambda msg, lvl="INFO": None
        progress = lambda p: None

        groups = find_duplicate_files(log, progress, str(tmp_path), min_size_bytes=1)

        assert len(groups) >= 1
        assert groups[0]["size"] == len(content)

    def test_no_duplicates(self, tmp_path):
        from modules.cleanup import find_duplicate_files
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")

        log = lambda msg, lvl="INFO": None
        progress = lambda p: None

        groups = find_duplicate_files(log, progress, str(tmp_path))
        assert len(groups) == 0

    def test_nonexistent_dir(self):
        from modules.cleanup import find_duplicate_files
        log = lambda msg, lvl="INFO": None
        progress = lambda p: None

        groups = find_duplicate_files(log, progress, "/nonexistent/path")
        assert groups == []

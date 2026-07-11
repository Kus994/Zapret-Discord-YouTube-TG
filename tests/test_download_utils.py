"""
test_download_utils.py — Тесты общего модуля скачивания.
"""

import pytest
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestDownloadUtils:
    """Тесты функций скачивания."""

    def test_ssl_ctx(self):
        from modules.download_utils import ssl_ctx
        ctx = ssl_ctx()
        assert ctx is not None
        assert ctx.check_hostname is True

    def test_extract_zip(self, tmp_path):
        from modules.download_utils import extract_zip

        # Создаём тестовый ZIP
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(str(zip_path), 'w') as zf:
            zf.writestr("test.txt", "hello world")
            zf.writestr("subdir/nested.txt", "nested content")

        dest = tmp_path / "extracted"
        dest.mkdir()

        extract_zip(str(zip_path), str(dest))

        assert (dest / "test.txt").exists()
        assert (dest / "subdir" / "nested.txt").exists()
        assert (dest / "test.txt").read_text() == "hello world"

    def test_extract_zip_with_progress(self, tmp_path):
        from modules.download_utils import extract_zip

        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(str(zip_path), 'w') as zf:
            zf.writestr("file1.txt", "content1")
            zf.writestr("file2.txt", "content2")

        dest = tmp_path / "extracted2"
        dest.mkdir()

        progress_values = []
        extract_zip(str(zip_path), str(dest), progress_cb=lambda p: progress_values.append(p))

        assert len(progress_values) > 0
        assert progress_values[-1] == 1.0

    def test_extract_zip_slip_protection(self, tmp_path):
        from modules.download_utils import extract_zip

        # Создаём ZIP с path traversal попыткой
        zip_path = tmp_path / "malicious.zip"
        with zipfile.ZipFile(str(zip_path), 'w') as zf:
            zf.writestr("../../../etc/passwd", "malicious")

        dest = tmp_path / "safe_dest"
        dest.mkdir()

        extract_zip(str(zip_path), str(dest))

        # Файл НЕ должен появиться за пределами dest
        assert not (tmp_path / "etc" / "passwd").exists()

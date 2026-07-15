"""
downloader.py — KUS Pro
Скачивает релизы с GitHub API.
Поддерживает: .zip (распаковывает), .exe (сохраняет как есть).
"""

import os
import tempfile
import urllib.error
import zipfile
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal

from modules.download_utils import (
    ssl_ctx as _ssl_ctx,
    get_latest_release as _get_latest_release,
    download_file as _download_file,
    extract_zip as _extract_zip,
)


class DownloadWorker(QThread):
    """
    Параметры:
      dest_dir      — куда сохранять/распаковывать
      owner, repo   — GitHub репозиторий
      asset_suffix  — суффикс нужного файла (.zip, _windows.exe, …)
      direct_url    — если задан, не обращаемся к API
    """
    log      = pyqtSignal(str, str)
    progress = pyqtSignal(float)
    done     = pyqtSignal(bool, str)

    def __init__(self, dest_dir, owner="", repo="",
                 asset_suffix=".zip", direct_url="", parent=None):
        super().__init__(parent)
        self._dest   = dest_dir
        self._owner  = owner
        self._repo   = repo
        self._suffix = asset_suffix
        self._url    = direct_url

    def run(self):
        try:
            # 1. Определяем URL
            if self._url:
                url  = self._url
                fname = Path(url).name or "download"
                tag  = ""
            else:
                self.log.emit("Запрос к GitHub API…", "INFO")
                url, fname, tag = _get_latest_release(
                    self._owner, self._repo, self._suffix)
                self.log.emit(
                    "Найден релиз: {}  ({})".format(tag, fname), "OK")

            # 2. Скачиваем во временный файл
            self.log.emit("Загрузка: {}".format(fname), "INFO")
            suffix = Path(fname).suffix or ".tmp"
            # NamedTemporaryFile(delete=False) вместо mktemp(): mktemp()
            # лишь придумывает имя, не создавая файл — между "придумали имя"
            # и "открыли его" есть окно для race condition. Здесь файл
            # создаётся атомарно, сразу занимая своё имя.
            tmp_fd = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
            tmp = tmp_fd.name
            tmp_fd.close()
            _download_file(url, tmp,
                           progress_cb=lambda p: self.progress.emit(p))
            self.log.emit("Загружено ✓  ({:.1f} МБ)".format(
                os.path.getsize(tmp) / 1024**2), "OK")

            Path(self._dest).mkdir(parents=True, exist_ok=True)

            # 3. Если ZIP — распаковываем; иначе кладём рядом
            if suffix.lower() == ".zip":
                self.log.emit("Распаковка…", "INFO")
                _extract_zip(tmp, self._dest,
                             progress_cb=lambda p: self.progress.emit(p))
            else:
                # EXE или другой бинарник — просто копируем
                target = Path(self._dest) / fname
                import shutil
                shutil.move(tmp, str(target))
                self.log.emit("Сохранён: {}".format(target), "OK")

            try:
                os.unlink(tmp)
            except OSError:
                pass

            self.progress.emit(1.0)
            self.done.emit(True,
                "Успешно установлено в {}".format(self._dest))

        except urllib.error.URLError as e:
            msg = "Ошибка сети: {}".format(getattr(e, "reason", e))
            self.log.emit(msg, "ERR")
            self.done.emit(False, msg)
        except zipfile.BadZipFile:
            msg = "Повреждённый ZIP-архив"
            self.log.emit(msg, "ERR")
            self.done.emit(False, msg)
        except Exception as e:
            msg = "Ошибка: {}".format(e)
            self.log.emit(msg, "ERR")
            self.done.emit(False, msg)

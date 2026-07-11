"""
auto_updater.py — KUS Pro
Автообновление Zapret и TgProxy с GitHub.
Проверяет последний релиз, скачивает, устанавливает, удаляет старые версии.
"""

import os
import json
import shutil
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

from PyQt5.QtCore import QThread, pyqtSignal

from app_paths import ZAPRET_DIR, TG_PROXY_DIR
from modules.download_utils import (
    ssl_ctx as _ssl_ctx,
    get_latest_release as _get_latest_release,
    download_file as _download_file,
    extract_zip as _extract_zip,
)


def _norm_version(v: str) -> str:
    """Нормализует версию: убирает префикс 'v' для сравнения."""
    return v.lstrip("vV") if v else v


# ── Zapret ────────────────────────────────────────────────────────── #

ZAPRET_OWNER = "Flowseal"
ZAPRET_REPO = "zapret-discord-youtube"
ZAPRET_SUFFIX = ".zip"


def get_zapret_installed_version() -> Optional[str]:
    """Возвращает имя текущей установленной версии zapret (папка)."""
    vf = ZAPRET_DIR / "current_version.txt"
    if vf.exists():
        name = vf.read_text(encoding="utf-8").strip()
        if (ZAPRET_DIR / name).exists():
            return name
    # Fallback — берём первую найденную папку с service.bat
    if ZAPRET_DIR.exists():
        try:
            for p in sorted(ZAPRET_DIR.iterdir()):
                if p.is_dir() and (p / "service.bat").exists():
                    return p.name
        except OSError:
            pass
    return None


def get_zapret_latest_version() -> Optional[str]:
    """Возвращает tag_name последнего релиза zapret с GitHub."""
    try:
        _, _, tag = _get_latest_release(ZAPRET_OWNER, ZAPRET_REPO, ZAPRET_SUFFIX)
        return tag
    except Exception:
        return None


def update_zapret(log_func=None, progress_func=None) -> Tuple[bool, str]:
    """
    Скачивает последний релиз zapret, распаковывает в новую папку,
    обновляет current_version.txt, удаляет старые версии.
    Возвращает (success, message).
    """
    log = log_func or (lambda m, *a: None)
    progress = progress_func or (lambda p: None)
    tmp = None

    try:
        log("Проверка обновлений Zapret...", "INFO")
        url, fname, tag = _get_latest_release(ZAPRET_OWNER, ZAPRET_REPO, ZAPRET_SUFFIX)
        log(f"Последний релиз: {tag} ({fname})", "OK")

        installed = get_zapret_installed_version()
        if installed and _norm_version(installed) == _norm_version(tag):
            log(f"Zapret уже обновлён (ver: {tag})", "OK")
            return True, "Уже обновлено"

        # Скачиваем
        log("Загрузка...", "INFO")
        tmp_fd = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        tmp = tmp_fd.name
        tmp_fd.close()
        _download_file(url, tmp, progress_cb=lambda p: progress(p * 0.8))

        # Проверяем что файл не пустой
        if os.path.getsize(tmp) < 1024:
            raise ValueError("Скачанный файл слишком малозагружен ({:.0f} байт)".format(
                os.path.getsize(tmp)))

        log(f"Загружено ({os.path.getsize(tmp) / 1024**2:.1f} МБ)", "OK")

        # Распаковываем в новую папку
        ZAPRET_DIR.mkdir(parents=True, exist_ok=True)
        new_dir = ZAPRET_DIR / tag
        if new_dir.exists():
            shutil.rmtree(new_dir, ignore_errors=True)
        new_dir.mkdir(parents=True, exist_ok=True)
        log(f"Распаковка в {new_dir.name}...", "INFO")
        _extract_zip(tmp, str(new_dir), progress_cb=lambda p: progress(0.8 + p * 0.15))

        # Обновляем current_version.txt
        (ZAPRET_DIR / "current_version.txt").write_text(tag, encoding="utf-8")

        # Удаляем старые версии (кроме текущей)
        deleted = 0
        try:
            for p in list(ZAPRET_DIR.iterdir()):  # list() — копия для безопасной итерации
                if p.is_dir() and p.name != tag and (p / "service.bat").exists():
                    try:
                        shutil.rmtree(p)
                        log(f"Удалена старая версия: {p.name}", "INFO")
                        deleted += 1
                    except PermissionError:
                        log(f"Папка занята: {p.name}", "WARN")
                    except Exception as e:
                        log(f"Не удалось удалить {p.name}: {e}", "WARN")
        except OSError:
            pass  # iterdir может упасть — не критично

        progress(1.0)
        msg = f"Zapret обновлён до {tag}"
        if deleted:
            msg += f" (удалено {deleted} старых версий)"
        log(msg, "OK")
        return True, msg

    except Exception as e:
        log(f"Ошибка обновления Zapret: {e}", "ERR")
        return False, str(e)

    finally:
        # Гарантированно удаляем temp-файл
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass


# ── TgProxy ───────────────────────────────────────────────────────── #

TG_PROXY_OWNER = "Flowseal"
TG_PROXY_REPO = "tg-ws-proxy"
TG_PROXY_SUFFIX = "_windows.exe"


def get_tg_proxy_installed_version() -> Optional[str]:
    """Возвращает tag_name установленной версии TgProxy."""
    vf = TG_PROXY_DIR / "current_version.txt"
    if vf.exists():
        return vf.read_text(encoding="utf-8").strip()
    return None


def get_tg_proxy_latest_version() -> Optional[str]:
    """Возвращает tag_name последнего релиза TgProxy с GitHub."""
    try:
        _, _, tag = _get_latest_release(TG_PROXY_OWNER, TG_PROXY_REPO, TG_PROXY_SUFFIX)
        return tag
    except Exception:
        return None


def update_tg_proxy(log_func=None, progress_func=None) -> Tuple[bool, str]:
    """
    Скачивает последний релиз TgProxy, заменяет exe, удаляет старые.
    Возвращает (success, message).
    """
    log = log_func or (lambda m, *a: None)
    progress = progress_func or (lambda p: None)
    tmp = None

    try:
        log("Проверка обновлений TgProxy...", "INFO")
        url, fname, tag = _get_latest_release(TG_PROXY_OWNER, TG_PROXY_REPO, TG_PROXY_SUFFIX)
        log(f"Последний релиз: {tag} ({fname})", "OK")

        installed = get_tg_proxy_installed_version()
        if installed and _norm_version(installed) == _norm_version(tag):
            log(f"TgProxy уже обновлён (ver: {tag})", "OK")
            return True, "Уже обновлено"

        # Скачиваем
        log("Загрузка...", "INFO")
        TG_PROXY_DIR.mkdir(parents=True, exist_ok=True)
        tmp_fd = tempfile.NamedTemporaryFile(suffix=".exe", delete=False)
        tmp = tmp_fd.name
        tmp_fd.close()
        _download_file(url, tmp, progress_cb=lambda p: progress(p * 0.8))

        # Проверяем что файл не пустой
        if os.path.getsize(tmp) < 1024:
            raise ValueError("Скачанный файл слишком малозагружен ({:.0f} байт)".format(
                os.path.getsize(tmp)))

        log(f"Загружено ({os.path.getsize(tmp) / 1024**2:.1f} МБ)", "OK")

        # Удаляем старый exe (кроме запущенного)
        for old in TG_PROXY_DIR.glob("TgWsProxy*.exe"):
            try:
                os.unlink(old)
                log(f"Удалён старый: {old.name}", "INFO")
            except PermissionError:
                log(f"Файл занят (запущен?): {old.name}", "WARN")
                # Пробуем переименовать старый файл чтобы освободить имя
                try:
                    old.rename(old.with_suffix(".exe.old"))
                except Exception:
                    pass
            except Exception:
                pass

        # Копируем новый (shutil.move может упасть если файл занят)
        target = TG_PROXY_DIR / fname
        try:
            shutil.move(tmp, str(target))
        except PermissionError:
            # Файл занят — пробуем записать через rename
            tmp_target = target.with_suffix(".exe.new")
            shutil.move(tmp, str(tmp_target))
            # Пробуем удалить целевой и переименовать новый
            try:
                target.unlink(missing_ok=True)
                tmp_target.rename(target)
            except PermissionError:
                log(f"Не удалось заменить {target.name} — файл запущен?", "WARN")
                log(f"Новый файл сохранён как {tmp_target.name}", "INFO")

        # Сохраняем версию
        (TG_PROXY_DIR / "current_version.txt").write_text(tag, encoding="utf-8")

        progress(1.0)
        msg = f"TgProxy обновлён до {tag}"
        log(msg, "OK")
        return True, msg

    except Exception as e:
        log(f"Ошибка обновления TgProxy: {e}", "ERR")
        return False, str(e)

    finally:
        # Гарантированно удаляем temp-файл
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass


# ── Combined updater thread ───────────────────────────────────────── #

class AutoUpdateWorker(QThread):
    """Фоновый поток для проверки и установки обновлений."""
    log = pyqtSignal(str, str)
    progress = pyqtSignal(float)
    done = pyqtSignal(str)  # summary message

    def __init__(self, update_zapret=True, update_tg_proxy=True, parent=None):
        super().__init__(parent)
        self._do_zapret = update_zapret
        self._do_tg = update_tg_proxy

    def run(self):
        results = []

        if self._do_zapret:
            ok, msg = update_zapret(
                log_func=lambda m, s="INFO": self.log.emit(m, s),
                progress_func=lambda p: self.progress.emit(p * 0.5),
            )
            results.append(("Zapret", ok, msg))

        if self._do_tg:
            ok, msg = update_tg_proxy(
                log_func=lambda m, s="INFO": self.log.emit(m, s),
                progress_func=lambda p: self.progress.emit(0.5 + p * 0.5),
            )
            results.append(("TgProxy", ok, msg))

        self.progress.emit(1.0)

        # Формируем итоговое сообщение
        updated = [name for name, ok, result_msg in results
                   if ok and result_msg != "Уже обновлено"]
        skipped = [name for name, ok, result_msg in results
                   if ok and result_msg == "Уже обновлено"]
        errors = [name for name, ok, result_msg in results if not ok]

        parts = []
        if updated:
            parts.append("Обновлены: " + ", ".join(updated))
        if skipped:
            parts.append("Уже актуальны: " + ", ".join(skipped))
        if errors:
            parts.append("Ошибки: " + ", ".join(errors))

        summary = "; ".join(parts) if parts else "Нет компонентов для обновления"
        self.done.emit(summary)


# ── Проверка обновлений KUS Pro ────────────────────────────────────── #

def check_kus_pro_update(log_func=None):
    """Проверяет, есть ли новая версия KUS Pro на GitHub.
    Возвращает (has_update, current_version, latest_version, download_url)."""
    from theme import VERSION

    try:
        api = "https://api.github.com/repos/Kus993/Zapret-Discord-YouTube-TG/releases/latest"
        headers = {
            "User-Agent": "KUS-Pro/3.0",
            "Accept": "application/vnd.github+json",
        }
        req = urllib.request.Request(api, headers=headers)
        with urllib.request.urlopen(req, timeout=15, context=_ssl_ctx()) as r:
            data = json.loads(r.read().decode())

        tag = data.get("tag_name", "")
        # Убираем "v" из тега если есть
        latest = tag.lstrip("v")
        current = VERSION

        # Сравниваем версии
        def parse_ver(v):
            try:
                return tuple(int(x) for x in v.split("."))
            except (ValueError, AttributeError):
                return (0,)

        has_update = parse_ver(latest) > parse_ver(current)

        # Ищем exe файл для скачивания
        download_url = ""
        for asset in data.get("assets", []):
            if asset["name"].lower().endswith(".exe"):
                download_url = asset["browser_download_url"]
                break

        if log_func:
            if has_update:
                log_func("Доступно обновление KUS Pro: {} → {}".format(current, latest), "INFO")
            else:
                log_func("KUS Pro актуален (v{})".format(current), "OK")

        return has_update, current, latest, download_url

    except Exception as e:
        if log_func:
            log_func("Не удалось проверить обновления: {}".format(e), "WARN")
        return False, VERSION, "", ""
